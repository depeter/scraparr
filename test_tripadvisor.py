#!/usr/bin/env python3
"""
Standalone test script for TripAdvisor scraper
"""

import asyncio
import json
import re
import random
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    exit(1)


class TripAdvisorTest:
    """Test class for TripAdvisor scraping"""

    BASE_URL = "https://www.tripadvisor.com"
    GRAPHQL_URL = "https://www.tripadvisor.com/data/graphql/ids"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    GRAPHQL_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.tripadvisor.com",
        "Referer": "https://www.tripadvisor.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self):
        self.session_cookies = {}
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def cleanup(self):
        await self.http_client.aclose()

    async def init_session(self):
        """Initialize session by visiting TripAdvisor homepage"""
        print("Initializing session...")

        try:
            response = await self.http_client.get(
                self.BASE_URL,
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=30.0
            )

            if hasattr(response, 'cookies'):
                self.session_cookies = dict(response.cookies)
                print(f"Session initialized with {len(self.session_cookies)} cookies")

        except Exception as e:
            print(f"Warning: Could not initialize session: {str(e)}")

    async def search_location_graphql(self, city: str, country: str) -> Optional[int]:
        """Search for a location using GraphQL API"""
        print(f"Searching for {city}, {country}...")

        search_query = f"{city}, {country}"

        payload = [{
            "query": "84b17ed122fbdbd4",
            "variables": {
                "request": {
                    "query": search_query,
                    "limit": 10,
                    "scope": "WORLDWIDE",
                    "locale": "en-US",
                    "scopeGeoId": 1,
                    "searchCenter": None,
                    "types": ["LOCATION"],
                    "locationTypes": ["GEO", "AIRPORT", "ACCOMMODATION", "ATTRACTION", "ATTRACTION_PRODUCT", "EATERY", "NEIGHBORHOOD"],
                    "userId": None,
                    "articleCategories": []
                }
            }
        }]

        request_id = hashlib.md5(f"{search_query}{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        headers = {
            **self.GRAPHQL_HEADERS,
            "X-Requested-By": request_id,
        }

        try:
            response = await self.http_client.post(
                self.GRAPHQL_URL,
                json=payload,
                headers=headers,
                cookies=self.session_cookies,
                timeout=30.0
            )

            print(f"GraphQL response status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"GraphQL response: {json.dumps(data, indent=2)[:500]}...")

                    if isinstance(data, list) and len(data) > 0:
                        results = data[0].get('data', {}).get('Typeahead_autocomplete', {}).get('results', [])
                        print(f"Found {len(results)} results")

                        for result in results:
                            details = result.get('details', {})
                            place_type = details.get('placeType')
                            print(f"  - {details.get('localizedName')} (type: {place_type})")

                            if place_type in ['GEO', 'CITY', 'REGION']:
                                loc_id = details.get('locationId')
                                if loc_id:
                                    print(f"Found location ID: {loc_id}")
                                    return int(loc_id)

                                url = details.get('url', '')
                                match = re.search(r'-g(\d+)-', url)
                                if match:
                                    return int(match.group(1))
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {str(e)}")
            else:
                print(f"GraphQL search returned status {response.status_code}")
                print(f"Response: {response.text[:500]}")

        except Exception as e:
            print(f"Error in GraphQL search: {str(e)}")

        return None

    async def fetch_attractions_page(self, geo_id: int, city: str, offset: int = 0) -> str:
        """Fetch attractions page and return HTML"""
        list_url = f"{self.BASE_URL}/Attractions-g{geo_id}-Activities-oa{offset}-{city.replace(' ', '_')}.html"
        print(f"Fetching: {list_url}")

        try:
            response = await self.http_client.get(
                list_url,
                headers=self.DEFAULT_HEADERS,
                cookies=self.session_cookies,
                follow_redirects=True,
                timeout=60.0
            )

            print(f"Response status: {response.status_code}")
            print(f"Response length: {len(response.text)} bytes")

            return response.text

        except Exception as e:
            print(f"Error fetching page: {str(e)}")
            return ""

    def extract_from_json_ld(self, html: str) -> List[Dict]:
        """Extract POI data from JSON-LD structured data"""
        pois = []

        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

        print(f"Found {len(matches)} JSON-LD script tags")

        for i, match in enumerate(matches):
            try:
                data = json.loads(match.strip())
                print(f"\nJSON-LD #{i+1} type: {data.get('@type', 'unknown')}")

                if data.get('@type') == 'ItemList':
                    items = data.get('itemListElement', [])
                    print(f"  ItemList with {len(items)} items")
                    for item in items[:3]:
                        print(f"    - {item.get('name', 'N/A')[:50]}")

                elif data.get('@type') in ['LocalBusiness', 'TouristAttraction', 'Restaurant', 'Hotel', 'LodgingBusiness']:
                    poi = self._parse_json_ld_item(data)
                    if poi:
                        pois.append(poi)
                        print(f"  Found POI: {poi.get('name', 'N/A')[:50]}")

            except json.JSONDecodeError as e:
                print(f"  JSON decode error: {str(e)[:50]}")
                continue

        return pois

    def _parse_json_ld_item(self, data: Dict) -> Optional[Dict]:
        """Parse a JSON-LD item"""
        try:
            url = data.get('url', '') or data.get('@id', '')
            location_id = None

            if url:
                match = re.search(r'-d(\d+)-', url)
                if match:
                    location_id = match.group(1)

            name = data.get('name', '')
            if not name or name.startswith('Review of:'):
                return None

            rating = None
            rating_count = None
            aggregate_rating = data.get('aggregateRating', {})
            if aggregate_rating:
                rating = aggregate_rating.get('ratingValue')
                rating_count = aggregate_rating.get('reviewCount')

            latitude = None
            longitude = None
            geo = data.get('geo', {})
            if geo:
                latitude = geo.get('latitude')
                longitude = geo.get('longitude')

            address_data = data.get('address', {})
            address = ''
            if isinstance(address_data, dict):
                street = address_data.get('streetAddress', '')
                city = address_data.get('addressLocality', '')
                address = f"{street}, {city}".strip(', ')

            return {
                'locationId': location_id,
                'name': name,
                'url': url,
                'rating': rating,
                'reviewCount': rating_count,
                'latitude': latitude,
                'longitude': longitude,
                'address': address,
                'description': data.get('description', '')[:100],
            }

        except Exception as e:
            return None

    def extract_from_html(self, html: str) -> List[Dict]:
        """Extract POI data from HTML elements"""
        pois = []

        # Look for attraction links
        url_pattern = r'href="(/Attraction_Review-g\d+-d(\d+)-[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(url_pattern, html)

        seen = set()
        for url, loc_id, name in matches:
            if loc_id in seen:
                continue
            seen.add(loc_id)

            name = name.strip()
            name = re.sub(r'^Review of:\s*', '', name)
            name = name.replace('&amp;', '&').replace('&#39;', "'")

            if not name or name.startswith('Review') or len(name) < 3:
                continue

            pois.append({
                'locationId': loc_id,
                'name': name,
                'url': f"{self.BASE_URL}{url}",
            })

        return pois

    def analyze_html_structure(self, html: str):
        """Analyze the HTML structure to understand available data"""
        print("\n" + "="*80)
        print("HTML Structure Analysis")
        print("="*80)

        # Check for common data patterns
        patterns = {
            '__WEB_CONTEXT__': r'window\.__WEB_CONTEXT__',
            'JSON-LD scripts': r'type=["\']application/ld\+json["\']',
            'data-location-id': r'data-location-id="(\d+)"',
            'Attraction_Review links': r'/Attraction_Review-g\d+-d\d+',
            '"locationId"': r'"locationId"\s*:\s*"?\d+"?',
            '"rating"': r'"rating"\s*:\s*[\d.]+',
            '"latitude"': r'"latitude"\s*:\s*-?[\d.]+',
            '"longitude"': r'"longitude"\s*:\s*-?[\d.]+',
        }

        for name, pattern in patterns.items():
            matches = re.findall(pattern, html)
            print(f"{name}: {len(matches)} occurrences")

        # Look for rating bubbles
        rating_pattern = r'bubble_(\d+)'
        rating_matches = re.findall(rating_pattern, html)
        if rating_matches:
            print(f"Rating bubbles: {len(rating_matches)} (values: {set(rating_matches)})")

        # Check for reviews count
        review_pattern = r'(\d+)\s*reviews?'
        review_matches = re.findall(review_pattern, html, re.IGNORECASE)
        if review_matches:
            print(f"Review counts found: {len(review_matches)} (examples: {review_matches[:5]})")


async def main():
    test = TripAdvisorTest()

    try:
        # Initialize session
        await test.init_session()
        await asyncio.sleep(2)

        # Search for Brussels
        geo_id = await test.search_location_graphql("Brussels", "Belgium")

        if not geo_id:
            print("\nFalling back to known Brussels geo_id: 188644")
            geo_id = 188644

        await asyncio.sleep(3)

        # Fetch attractions page
        html = await test.fetch_attractions_page(geo_id, "Brussels")

        if html:
            # Analyze HTML structure
            test.analyze_html_structure(html)

            # Try JSON-LD extraction
            print("\n" + "="*80)
            print("JSON-LD Extraction")
            print("="*80)
            json_ld_pois = test.extract_from_json_ld(html)
            print(f"\nExtracted {len(json_ld_pois)} POIs from JSON-LD")

            for poi in json_ld_pois[:5]:
                print(f"\n  Name: {poi.get('name', 'N/A')}")
                print(f"  ID: {poi.get('locationId', 'N/A')}")
                print(f"  Rating: {poi.get('rating', 'N/A')}")
                print(f"  Reviews: {poi.get('reviewCount', 'N/A')}")
                print(f"  Lat/Lng: {poi.get('latitude', 'N/A')}, {poi.get('longitude', 'N/A')}")

            # Try HTML extraction
            print("\n" + "="*80)
            print("HTML Element Extraction")
            print("="*80)
            html_pois = test.extract_from_html(html)
            print(f"\nExtracted {len(html_pois)} POIs from HTML")

            for poi in html_pois[:10]:
                print(f"  - {poi.get('name', 'N/A')[:50]} (ID: {poi.get('locationId')})")

            # Save sample HTML for inspection
            with open('/tmp/tripadvisor_sample.html', 'w') as f:
                f.write(html)
            print(f"\nSample HTML saved to /tmp/tripadvisor_sample.html")

    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

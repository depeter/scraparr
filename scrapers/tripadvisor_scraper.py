#!/usr/bin/env python3
"""
TripAdvisor Scraper for Scraparr
Uses TripAdvisor's internal GraphQL API to fetch attractions, restaurants, and hotels.

This scraper uses a two-step approach:
1. Search for POIs in a location using the GraphQL search endpoint
2. Fetch detailed information for each POI from individual pages

NOTE: TripAdvisor has rate limiting and bot detection. Use responsibly with appropriate delays.
"""

import sys
sys.path.insert(0, '/app/backend')

from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List, Optional
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Text, JSON, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
import random
import json
import re
from datetime import datetime
from urllib.parse import quote, urljoin
import hashlib


# European countries with major tourist destinations
EUROPEAN_COUNTRIES = {
    "austria": {"name": "Austria", "geo_id": 190410, "cities": ["Vienna", "Salzburg", "Innsbruck"]},
    "belgium": {"name": "Belgium", "geo_id": 188634, "cities": ["Brussels", "Bruges", "Antwerp", "Ghent"]},
    "croatia": {"name": "Croatia", "geo_id": 294453, "cities": ["Dubrovnik", "Split", "Zagreb"]},
    "czech-republic": {"name": "Czech Republic", "geo_id": 274684, "cities": ["Prague", "Brno", "Cesky Krumlov"]},
    "denmark": {"name": "Denmark", "geo_id": 189512, "cities": ["Copenhagen", "Aarhus", "Odense"]},
    "finland": {"name": "Finland", "geo_id": 189896, "cities": ["Helsinki", "Rovaniemi", "Turku"]},
    "france": {"name": "France", "geo_id": 187070, "cities": ["Paris", "Nice", "Lyon", "Marseille", "Bordeaux"]},
    "germany": {"name": "Germany", "geo_id": 187275, "cities": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"]},
    "greece": {"name": "Greece", "geo_id": 189398, "cities": ["Athens", "Santorini", "Mykonos", "Crete"]},
    "hungary": {"name": "Hungary", "geo_id": 274881, "cities": ["Budapest", "Debrecen", "Eger"]},
    "iceland": {"name": "Iceland", "geo_id": 189970, "cities": ["Reykjavik", "Akureyri", "Vik"]},
    "ireland": {"name": "Ireland", "geo_id": 186591, "cities": ["Dublin", "Galway", "Cork"]},
    "italy": {"name": "Italy", "geo_id": 187768, "cities": ["Rome", "Florence", "Venice", "Milan", "Naples"]},
    "netherlands": {"name": "Netherlands", "geo_id": 188553, "cities": ["Amsterdam", "Rotterdam", "The Hague"]},
    "norway": {"name": "Norway", "geo_id": 190455, "cities": ["Oslo", "Bergen", "Tromso"]},
    "poland": {"name": "Poland", "geo_id": 274723, "cities": ["Krakow", "Warsaw", "Gdansk"]},
    "portugal": {"name": "Portugal", "geo_id": 189140, "cities": ["Lisbon", "Porto", "Faro"]},
    "romania": {"name": "Romania", "geo_id": 294457, "cities": ["Bucharest", "Brasov", "Cluj-Napoca"]},
    "spain": {"name": "Spain", "geo_id": 187427, "cities": ["Barcelona", "Madrid", "Seville", "Valencia", "Granada"]},
    "sweden": {"name": "Sweden", "geo_id": 189806, "cities": ["Stockholm", "Gothenburg", "Malmo"]},
    "switzerland": {"name": "Switzerland", "geo_id": 188045, "cities": ["Zurich", "Geneva", "Lucerne", "Interlaken"]},
    "turkey": {"name": "Turkey", "geo_id": 293969, "cities": ["Istanbul", "Cappadocia", "Antalya"]},
    "united-kingdom": {"name": "United Kingdom", "geo_id": 186216, "cities": ["London", "Edinburgh", "Manchester", "Liverpool"]},
}

# POI categories on TripAdvisor
POI_CATEGORIES = {
    "attractions": "attractions",
    "restaurants": "restaurants",
    "hotels": "hotels",
}


class TripAdvisorScraper(BaseScraper):
    """
    Scraper for TripAdvisor using internal GraphQL API and page scraping.

    This scraper:
    1. Uses GraphQL API to search for locations
    2. Fetches the listing pages to get POI lists
    3. Extracts hidden JSON data from script tags for rich POI details
    4. Falls back to HTML parsing when JSON extraction fails
    """

    scraper_type = ScraperType.WEB

    # TripAdvisor base URLs
    BASE_URL = "https://www.tripadvisor.com"
    GRAPHQL_URL = "https://www.tripadvisor.com/data/graphql/ids"

    # Default headers to mimic a browser
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

    # GraphQL headers
    GRAPHQL_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.tripadvisor.com",
        "Referer": "https://www.tripadvisor.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_delay = 3.0
        self.max_delay = 8.0
        self.request_count = 0
        self.session_cookies = {}

    def define_tables(self) -> List[Table]:
        """Define database tables for TripAdvisor data"""
        pois_table = Table(
            'pois',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('tripadvisor_id', String(50), unique=True, nullable=False),
            Column('name', String(500), nullable=False),
            Column('category', String(50)),
            Column('subcategory', String(100)),
            Column('description', Text),
            Column('url', String(1000)),
            Column('rating', Float),
            Column('rating_count', Integer),
            Column('ranking', String(200)),
            Column('price_level', String(10)),
            Column('price_range', String(100)),
            Column('address', String(500)),
            Column('city', String(255)),
            Column('country', String(100)),
            Column('country_code', String(5)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('phone', String(50)),
            Column('website', String(1000)),
            Column('email', String(255)),
            Column('hours', JSON),
            Column('amenities', JSON),
            Column('cuisine_types', JSON),
            Column('hotel_class', String(20)),
            Column('image_url', String(1000)),
            Column('images', JSON),
            Column('awards', JSON),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        reviews_table = Table(
            'reviews',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('review_id', String(50), unique=True, nullable=False),
            Column('poi_id', String(50), nullable=False),
            Column('title', String(500)),
            Column('text', Text),
            Column('rating', Integer),
            Column('published_date', DateTime),
            Column('visit_date', String(50)),
            Column('trip_type', String(50)),
            Column('reviewer_name', String(200)),
            Column('reviewer_location', String(200)),
            Column('reviewer_contributions', Integer),
            Column('helpful_votes', Integer),
            Column('owner_response', Text),
            Column('owner_response_date', DateTime),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        scrape_progress_table = Table(
            'scrape_progress',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('country', String(100)),
            Column('city', String(200)),
            Column('category', String(50)),
            Column('offset', Integer, default=0),
            Column('total_found', Integer),
            Column('completed', Integer, default=0),
            Column('processed_at', DateTime, default=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        return [pois_table, reviews_table, scrape_progress_table]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape TripAdvisor for POIs

        Params:
            country: Country slug or "all"
            city: Optional specific city
            category: "attractions", "restaurants", "hotels", or "all"
            max_results: Maximum results per city/category (default: 100)
            include_reviews: Whether to scrape reviews (default: False)
            max_reviews_per_poi: Max reviews per POI (default: 10)
            min_delay: Min delay between requests (default: 3.0)
            max_delay: Max delay between requests (default: 8.0)
            resume: Resume from last progress (default: True)
        """
        country_param = params.get('country', 'belgium')
        city_param = params.get('city')
        category_param = params.get('category', 'attractions')
        max_results = params.get('max_results', 100)
        include_reviews = params.get('include_reviews', False)
        max_reviews_per_poi = params.get('max_reviews_per_poi', 10)
        self.min_delay = params.get('min_delay', 3.0)
        self.max_delay = params.get('max_delay', 8.0)
        resume = params.get('resume', True)

        self.log(f"Starting TripAdvisor scrape")
        self.log(f"Country: {country_param}, City: {city_param}, Category: {category_param}")
        self.log(f"Max results per city: {max_results}, Include reviews: {include_reviews}")
        self.log(f"Rate limiting: {self.min_delay}s - {self.max_delay}s delay between requests")

        # Determine countries to scrape
        countries_to_scrape = []
        if country_param.lower() == 'all':
            countries_to_scrape = list(EUROPEAN_COUNTRIES.keys())
            self.log(f"Scraping all {len(countries_to_scrape)} European countries")
        elif country_param.lower() in EUROPEAN_COUNTRIES:
            countries_to_scrape = [country_param.lower()]
        else:
            self.log(f"Unknown country: {country_param}. Available: {', '.join(EUROPEAN_COUNTRIES.keys())}", level="error")
            raise ValueError(f"Unknown country: {country_param}")

        # Determine categories to scrape
        categories_to_scrape = []
        if category_param.lower() == 'all':
            categories_to_scrape = list(POI_CATEGORIES.keys())
        elif category_param.lower() in POI_CATEGORIES:
            categories_to_scrape = [category_param.lower()]
        else:
            self.log(f"Unknown category: {category_param}. Available: attractions, restaurants, hotels, all", level="error")
            raise ValueError(f"Unknown category: {category_param}")

        all_pois = []
        seen_ids = set()

        # Initialize session
        await self._init_session()

        for country_slug in countries_to_scrape:
            country_info = EUROPEAN_COUNTRIES[country_slug]
            country_name = country_info['name']
            cities = [city_param] if city_param else country_info['cities']

            self.log(f"\n{'='*60}")
            self.log(f"Scraping {country_name}")
            self.log(f"{'='*60}")

            for city in cities:
                for category in categories_to_scrape:
                    self.log(f"\nScraping {category} in {city}, {country_name}...")

                    try:
                        start_offset = 0
                        if resume:
                            start_offset = await self._get_progress(country_slug, city, category)
                            if start_offset > 0:
                                self.log(f"Resuming from offset {start_offset}")

                        pois = await self._scrape_category(
                            city=city,
                            country=country_name,
                            country_slug=country_slug,
                            category=category,
                            max_results=max_results,
                            include_reviews=include_reviews,
                            max_reviews_per_poi=max_reviews_per_poi,
                            start_offset=start_offset,
                            seen_ids=seen_ids
                        )

                        all_pois.extend(pois)
                        self.log(f"Found {len(pois)} {category} in {city}")

                        await self._save_progress(country_slug, city, category, len(pois), completed=True)

                    except Exception as e:
                        self.log(f"Error scraping {category} in {city}: {str(e)}", level="error")
                        import traceback
                        self.log(f"Traceback: {traceback.format_exc()}", level="error")
                        continue

                    await self.report_progress(
                        len(all_pois),
                        f"Scraped {len(all_pois)} POIs total. Last: {city}, {country_name}"
                    )

        self.log(f"\n{'='*60}")
        self.log(f"Scraping complete! Total unique POIs: {len(all_pois)}")
        self.log(f"{'='*60}")

        return all_pois

    async def _init_session(self):
        """Initialize session by visiting TripAdvisor homepage to get cookies"""
        self.log("Initializing session...")

        try:
            response = await self.http_client.get(
                self.BASE_URL,
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=30.0
            )

            if hasattr(response, 'cookies'):
                self.session_cookies = dict(response.cookies)
                self.log(f"Session initialized with {len(self.session_cookies)} cookies")

            await self._rate_limit()

        except Exception as e:
            self.log(f"Warning: Could not initialize session: {str(e)}", level="warning")

    async def _rate_limit(self):
        """Apply rate limiting between requests"""
        delay = random.uniform(self.min_delay, self.max_delay)
        self.request_count += 1

        if self.request_count % 10 == 0:
            delay += random.uniform(2.0, 5.0)
            self.log(f"Request #{self.request_count}: Extended delay {delay:.1f}s")

        await asyncio.sleep(delay)

    async def _scrape_category(
        self,
        city: str,
        country: str,
        country_slug: str,
        category: str,
        max_results: int,
        include_reviews: bool,
        max_reviews_per_poi: int,
        start_offset: int,
        seen_ids: set
    ) -> List[Dict[str, Any]]:
        """Scrape a specific category for a city"""

        pois = []
        offset = start_offset
        page_size = 30

        # First, search for the city to get its geo_id
        city_geo_id = await self._search_location_graphql(city, country)
        if not city_geo_id:
            self.log(f"Could not find geo_id for {city}, using country geo_id", level="warning")
            city_geo_id = EUROPEAN_COUNTRIES.get(country_slug, {}).get('geo_id', 0)
        else:
            self.log(f"Found geo_id {city_geo_id} for {city}")

        while len(pois) < max_results:
            await self._rate_limit()

            try:
                # Fetch POIs from the listing page
                page_pois = await self._fetch_pois_from_page(
                    city=city,
                    country=country,
                    category=category,
                    geo_id=city_geo_id,
                    offset=offset
                )

                if not page_pois:
                    self.log(f"No more {category} found at offset {offset}")
                    break

                # Process each POI
                new_pois_count = 0
                for poi_data in page_pois:
                    poi_id = str(poi_data.get('locationId') or poi_data.get('id', ''))
                    if not poi_id or poi_id in seen_ids:
                        continue

                    seen_ids.add(poi_id)

                    # Create POI record
                    poi = self._create_poi_record(poi_data, city, country, country_slug, category)
                    if poi:
                        if include_reviews and poi.get('url'):
                            await self._rate_limit()
                            reviews = await self._fetch_reviews(poi_id, poi.get('url', ''), max_reviews_per_poi)
                            poi['reviews'] = reviews

                        pois.append(poi)
                        new_pois_count += 1

                self.log(f"Page at offset {offset}: {len(page_pois)} results, {new_pois_count} new, {len(pois)} total")

                if len(pois) % 50 == 0:
                    await self._save_progress(country_slug, city, category, offset)

                offset += page_size

                if len(page_pois) < page_size:
                    break

            except Exception as e:
                self.log(f"Error fetching page at offset {offset}: {str(e)}", level="error")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}", level="error")
                break

        return pois

    async def _search_location_graphql(self, city: str, country: str) -> Optional[int]:
        """Search for a location using GraphQL API to get its geo_id"""

        await self._rate_limit()

        search_query = f"{city}, {country}"

        # GraphQL search payload
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
                    "locationTypes": ["GEO", "AIRPORT", "ACCOMMODATION", "ATTRACTION", "ATTRACTION_PRODUCT", "EATERY", "NEIGHBORHOOD", "AIRLINE", "SHOPPING", "UNIVERSITY", "GENERAL_HOSPITAL", "PORT", "FERRY", "CORPORATION", "VACATION_RENTAL", "SHIP", "CRUISE_LINE", "CAR_RENTAL_OFFICE"],
                    "userId": None,
                    "articleCategories": []
                }
            }
        }]

        # Generate a random request ID
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

            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        results = data[0].get('data', {}).get('Typeahead_autocomplete', {}).get('results', [])

                        for result in results:
                            details = result.get('details', {})
                            if details.get('placeType') in ['GEO', 'CITY', 'REGION']:
                                # Extract geo_id from URL or locationId
                                loc_id = details.get('locationId')
                                if loc_id:
                                    self.log(f"Found location: {details.get('localizedName')} (ID: {loc_id})")
                                    return int(loc_id)

                                # Try extracting from URL
                                url = details.get('url', '')
                                match = re.search(r'-g(\d+)-', url)
                                if match:
                                    return int(match.group(1))
                except json.JSONDecodeError as e:
                    self.log(f"JSON decode error: {str(e)}", level="warning")
            else:
                self.log(f"GraphQL search returned status {response.status_code}", level="warning")

        except Exception as e:
            self.log(f"Error in GraphQL search for {city}: {str(e)}", level="warning")

        # Fallback: try the TypeAheadJson endpoint
        return await self._search_location_typeahead(city, country)

    async def _search_location_typeahead(self, city: str, country: str) -> Optional[int]:
        """Fallback search using TypeAheadJson endpoint"""

        search_query = f"{city}, {country}"
        search_url = f"{self.BASE_URL}/TypeAheadJson"

        params = {
            "action": "API",
            "query": search_query,
            "types": "geo",
            "max": 5,
        }

        json_headers = {
            "User-Agent": self.DEFAULT_HEADERS["User-Agent"],
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/",
        }

        try:
            response = await self.http_client.get(
                search_url,
                params=params,
                headers=json_headers,
                cookies=self.session_cookies,
                timeout=30.0
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    results = data.get('results', [])

                    for result in results:
                        if result.get('type') == 'geo':
                            geo_id = result.get('value')
                            if geo_id:
                                match = re.search(r'g(\d+)', str(geo_id))
                                if match:
                                    return int(match.group(1))
                                elif isinstance(geo_id, int):
                                    return geo_id
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            self.log(f"Error in typeahead search for {city}: {str(e)}", level="warning")

        return None

    async def _fetch_pois_from_page(
        self,
        city: str,
        country: str,
        category: str,
        geo_id: int,
        offset: int
    ) -> List[Dict]:
        """Fetch POIs from TripAdvisor listing page and extract JSON data"""

        # Build URL based on category
        if category == "attractions":
            list_url = f"{self.BASE_URL}/Attractions-g{geo_id}-Activities-oa{offset}-{city.replace(' ', '_')}.html"
        elif category == "restaurants":
            list_url = f"{self.BASE_URL}/Restaurants-g{geo_id}-oa{offset}-{city.replace(' ', '_')}.html"
        elif category == "hotels":
            list_url = f"{self.BASE_URL}/Hotels-g{geo_id}-oa{offset}-{city.replace(' ', '_')}.html"
        else:
            return []

        self.log(f"Fetching: {list_url}")

        try:
            response = await self.http_client.get(
                list_url,
                headers=self.DEFAULT_HEADERS,
                cookies=self.session_cookies,
                follow_redirects=True,
                timeout=60.0
            )

            if response.status_code == 403:
                self.log("Received 403 Forbidden - TripAdvisor may be blocking requests", level="error")
                return []

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code} for {list_url}", level="warning")
                return []

            html = response.text

            # Try multiple extraction methods
            pois = []

            # Method 1: Extract from script tags containing JSON-LD structured data
            pois = self._extract_from_json_ld(html, category)
            if pois:
                self.log(f"Extracted {len(pois)} POIs from JSON-LD data")
                return pois

            # Method 2: Extract from __WEB_CONTEXT__ or similar JavaScript data
            pois = self._extract_from_web_context(html, category)
            if pois:
                self.log(f"Extracted {len(pois)} POIs from web context data")
                return pois

            # Method 3: Extract from embedded JSON in script tags
            pois = self._extract_from_script_json(html, category)
            if pois:
                self.log(f"Extracted {len(pois)} POIs from script JSON")
                return pois

            # Method 4: Fallback to HTML parsing
            pois = self._extract_from_html_elements(html, category)
            if pois:
                self.log(f"Extracted {len(pois)} POIs from HTML elements")
                return pois

            self.log("No POIs extracted from page", level="warning")
            return []

        except Exception as e:
            self.log(f"Error fetching {category} page: {str(e)}", level="error")
            return []

    def _extract_from_json_ld(self, html: str, category: str) -> List[Dict]:
        """Extract POI data from JSON-LD structured data in script tags"""
        pois = []

        try:
            # Find all script tags with JSON-LD
            json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

            for match in matches:
                try:
                    data = json.loads(match.strip())

                    # Handle ItemList (common for listing pages)
                    if data.get('@type') == 'ItemList':
                        for item in data.get('itemListElement', []):
                            poi = self._parse_json_ld_item(item, category)
                            if poi:
                                pois.append(poi)

                    # Handle single LocalBusiness, TouristAttraction, etc.
                    elif data.get('@type') in ['LocalBusiness', 'TouristAttraction', 'Restaurant', 'Hotel', 'LodgingBusiness']:
                        poi = self._parse_json_ld_item(data, category)
                        if poi:
                            pois.append(poi)

                    # Handle array of items
                    elif isinstance(data, list):
                        for item in data:
                            poi = self._parse_json_ld_item(item, category)
                            if poi:
                                pois.append(poi)

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.log(f"Error extracting JSON-LD: {str(e)}", level="warning")

        return pois

    def _parse_json_ld_item(self, data: Dict, category: str) -> Optional[Dict]:
        """Parse a JSON-LD item into POI format"""
        try:
            # Get URL and extract location ID
            url = data.get('url', '') or data.get('@id', '')
            location_id = None

            if url:
                match = re.search(r'-d(\d+)-', url)
                if match:
                    location_id = match.group(1)

            if not location_id:
                return None

            # Extract name
            name = data.get('name', '')
            if not name or name.startswith('Review of:'):
                return None

            # Extract rating
            rating = None
            rating_count = None
            aggregate_rating = data.get('aggregateRating', {})
            if aggregate_rating:
                rating = aggregate_rating.get('ratingValue')
                rating_count = aggregate_rating.get('reviewCount')

            # Extract address
            address_data = data.get('address', {})
            address = ''
            city = ''
            country = ''
            postal_code = ''

            if isinstance(address_data, dict):
                street = address_data.get('streetAddress', '')
                city = address_data.get('addressLocality', '')
                region = address_data.get('addressRegion', '')
                postal_code = address_data.get('postalCode', '')
                country = address_data.get('addressCountry', '')

                address_parts = [p for p in [street, city, region, postal_code] if p]
                address = ', '.join(address_parts)
            elif isinstance(address_data, str):
                address = address_data

            # Extract coordinates
            latitude = None
            longitude = None
            geo = data.get('geo', {})
            if geo:
                latitude = geo.get('latitude')
                longitude = geo.get('longitude')

            # Extract image
            image_url = None
            image = data.get('image')
            if image:
                if isinstance(image, str):
                    image_url = image
                elif isinstance(image, dict):
                    image_url = image.get('url')
                elif isinstance(image, list) and len(image) > 0:
                    if isinstance(image[0], str):
                        image_url = image[0]
                    elif isinstance(image[0], dict):
                        image_url = image[0].get('url')

            # Extract price range
            price_range = data.get('priceRange', '')

            # Extract description
            description = data.get('description', '')

            # Extract phone
            phone = data.get('telephone', '')

            return {
                'locationId': location_id,
                'name': name,
                'url': url if url.startswith('http') else f"{self.BASE_URL}{url}",
                'rating': float(rating) if rating else None,
                'reviewCount': int(rating_count) if rating_count else None,
                'address': address,
                'city': city,
                'country': country,
                'latitude': float(latitude) if latitude else None,
                'longitude': float(longitude) if longitude else None,
                'image': image_url,
                'priceRange': price_range,
                'description': description,
                'phone': phone,
            }

        except Exception as e:
            return None

    def _extract_from_web_context(self, html: str, category: str) -> List[Dict]:
        """Extract POI data from __WEB_CONTEXT__ JavaScript variable"""
        pois = []

        try:
            # Look for __WEB_CONTEXT__ data
            patterns = [
                r'window\.__WEB_CONTEXT__\s*=\s*(\{.+?\});?\s*(?:</script>|window\.)',
                r'__WEB_CONTEXT__\s*=\s*(\{.+?\});?\s*(?:</script>|window\.)',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                for match in matches:
                    try:
                        # Clean up the JSON
                        json_str = match.strip().rstrip(';')

                        # Handle potential undefined values
                        json_str = re.sub(r':\s*undefined\s*([,}])', r': null\1', json_str)

                        data = json.loads(json_str)

                        # Navigate to find POI data
                        extracted = self._find_pois_in_nested_data(data, category)
                        pois.extend(extracted)

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            self.log(f"Error extracting web context: {str(e)}", level="warning")

        return pois

    def _find_pois_in_nested_data(self, data: Any, category: str, depth: int = 0) -> List[Dict]:
        """Recursively find POI data in nested JSON structures"""
        pois = []

        if depth > 10:  # Prevent infinite recursion
            return pois

        if isinstance(data, dict):
            # Check if this looks like a POI
            if self._looks_like_poi(data, category):
                pois.append(data)
            else:
                # Recurse into nested objects
                for key, value in data.items():
                    if key in ['locations', 'results', 'data', 'items', 'attractions', 'restaurants', 'hotels']:
                        if isinstance(value, list):
                            for item in value:
                                pois.extend(self._find_pois_in_nested_data(item, category, depth + 1))
                        else:
                            pois.extend(self._find_pois_in_nested_data(value, category, depth + 1))
        elif isinstance(data, list):
            for item in data:
                pois.extend(self._find_pois_in_nested_data(item, category, depth + 1))

        return pois

    def _looks_like_poi(self, data: Dict, category: str) -> bool:
        """Check if a dict looks like a POI with useful data"""
        # Must have a location ID and name
        has_id = any(key in data for key in ['locationId', 'location_id', 'id', 'placeId'])
        has_name = 'name' in data and data['name'] and not str(data.get('name', '')).startswith('Review of:')

        # Should have at least one useful field
        has_useful_data = any(key in data for key in [
            'rating', 'averageRating', 'ratingValue',
            'reviewCount', 'numReviews',
            'latitude', 'longitude', 'geo', 'location',
            'address', 'streetAddress'
        ])

        return has_id and has_name and has_useful_data

    def _extract_from_script_json(self, html: str, category: str) -> List[Dict]:
        """Extract POI data from script tags containing JSON"""
        pois = []

        try:
            # Pattern to find script tags with JSON content
            script_pattern = r'<script[^>]*>(.*?)</script>'
            script_matches = re.findall(script_pattern, html, re.DOTALL)

            for script_content in script_matches:
                # Skip empty or very short scripts
                if len(script_content.strip()) < 100:
                    continue

                # Look for JSON-like structures
                json_patterns = [
                    r'"locations"\s*:\s*(\[.+?\])',
                    r'"attractions"\s*:\s*(\[.+?\])',
                    r'"restaurants"\s*:\s*(\[.+?\])',
                    r'"hotels"\s*:\s*(\[.+?\])',
                    r'"results"\s*:\s*(\[.+?\])',
                    r'"items"\s*:\s*(\[.+?\])',
                ]

                for pattern in json_patterns:
                    matches = re.findall(pattern, script_content, re.DOTALL)
                    for match in matches:
                        try:
                            items = json.loads(match)
                            if isinstance(items, list):
                                for item in items:
                                    if self._looks_like_poi(item, category):
                                        pois.append(item)
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            self.log(f"Error extracting script JSON: {str(e)}", level="warning")

        return pois

    def _extract_from_html_elements(self, html: str, category: str) -> List[Dict]:
        """Fallback: Extract POI data from HTML elements"""
        pois = []

        try:
            # Pattern for attraction/restaurant/hotel cards with data attributes
            # Look for links with location IDs and names
            if category == "attractions":
                url_pattern = r'href="(/Attraction_Review-g\d+-d(\d+)-[^"]+)"[^>]*>([^<]+)</a>'
            elif category == "restaurants":
                url_pattern = r'href="(/Restaurant_Review-g\d+-d(\d+)-[^"]+)"[^>]*>([^<]+)</a>'
            elif category == "hotels":
                url_pattern = r'href="(/Hotel_Review-g\d+-d(\d+)-[^"]+)"[^>]*>([^<]+)</a>'
            else:
                return pois

            matches = re.findall(url_pattern, html)
            seen = set()

            for url, loc_id, name in matches:
                if loc_id in seen:
                    continue
                seen.add(loc_id)

                # Clean up name
                name = name.strip()
                name = re.sub(r'^Review of:\s*', '', name)
                name = re.sub(r'<[^>]+>', '', name)  # Remove any HTML tags
                name = name.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')

                if not name or name.startswith('Review'):
                    continue

                pois.append({
                    'locationId': loc_id,
                    'name': name,
                    'url': f"{self.BASE_URL}{url}",
                })

            # If we found POIs but they lack details, try to fetch individual pages
            if pois:
                self.log(f"Found {len(pois)} POIs from HTML, fetching details...")

        except Exception as e:
            self.log(f"Error extracting from HTML: {str(e)}", level="warning")

        return pois

    def _create_poi_record(
        self,
        poi_data: Dict,
        city: str,
        country: str,
        country_slug: str,
        category: str
    ) -> Optional[Dict]:
        """Create a standardized POI record from extracted data"""

        try:
            location_id = str(poi_data.get('locationId') or poi_data.get('location_id') or poi_data.get('id') or '')
            if not location_id:
                return None

            name = poi_data.get('name', '')
            if not name or name.startswith('Review of:'):
                return None

            # Clean name
            name = re.sub(r'^Review of:\s*', '', name)
            name = name.replace('&amp;', '&').replace('&#39;', "'")

            # Build URL if not present
            url = poi_data.get('url', '')
            if not url and location_id:
                if category == "attractions":
                    url = f"{self.BASE_URL}/Attraction_Review-g0-d{location_id}"
                elif category == "restaurants":
                    url = f"{self.BASE_URL}/Restaurant_Review-g0-d{location_id}"
                elif category == "hotels":
                    url = f"{self.BASE_URL}/Hotel_Review-g0-d{location_id}"

            # Ensure URL doesn't end with #REVIEWS
            if url:
                url = re.sub(r'#REVIEWS$', '', url)

            # Extract rating
            rating = None
            for key in ['rating', 'averageRating', 'ratingValue']:
                if key in poi_data and poi_data[key] is not None:
                    try:
                        rating = float(poi_data[key])
                        break
                    except (ValueError, TypeError):
                        pass

            # Extract review count
            rating_count = None
            for key in ['reviewCount', 'numReviews', 'rating_count']:
                if key in poi_data and poi_data[key] is not None:
                    try:
                        rating_count = int(poi_data[key])
                        break
                    except (ValueError, TypeError):
                        pass

            # Extract coordinates
            latitude = None
            longitude = None

            if 'latitude' in poi_data:
                try:
                    latitude = float(poi_data['latitude'])
                except (ValueError, TypeError):
                    pass
            if 'longitude' in poi_data:
                try:
                    longitude = float(poi_data['longitude'])
                except (ValueError, TypeError):
                    pass

            # Check nested location/geo objects
            if latitude is None or longitude is None:
                for geo_key in ['geo', 'location', 'coordinates']:
                    geo = poi_data.get(geo_key, {})
                    if isinstance(geo, dict):
                        if latitude is None:
                            lat_val = geo.get('latitude') or geo.get('lat')
                            if lat_val:
                                try:
                                    latitude = float(lat_val)
                                except (ValueError, TypeError):
                                    pass
                        if longitude is None:
                            lng_val = geo.get('longitude') or geo.get('lng') or geo.get('lon')
                            if lng_val:
                                try:
                                    longitude = float(lng_val)
                                except (ValueError, TypeError):
                                    pass

            # Extract address
            address = poi_data.get('address', '') or poi_data.get('streetAddress', '')
            if isinstance(address, dict):
                address = address.get('street', '') or address.get('streetAddress', '')

            # Extract city from data or use provided city
            poi_city = poi_data.get('city') or city

            # Extract country from data or use provided country
            poi_country = poi_data.get('country') or country

            # Extract price info
            price_level = poi_data.get('priceLevel') or poi_data.get('price_level')
            price_range = poi_data.get('priceRange') or poi_data.get('price_range')

            # Extract subcategory
            subcategory = poi_data.get('subcategory') or poi_data.get('category') or poi_data.get('primaryCategory')
            if isinstance(subcategory, dict):
                subcategory = subcategory.get('name', '')
            elif isinstance(subcategory, list) and len(subcategory) > 0:
                subcategory = subcategory[0].get('name', '') if isinstance(subcategory[0], dict) else str(subcategory[0])

            # Extract cuisine types for restaurants
            cuisine_types = None
            if category == "restaurants":
                cuisines = poi_data.get('cuisines') or poi_data.get('cuisine') or []
                if cuisines:
                    cuisine_types = cuisines if isinstance(cuisines, list) else [cuisines]

            # Extract hotel class
            hotel_class = None
            if category == "hotels":
                hotel_class = poi_data.get('hotelClass') or poi_data.get('hotel_class')

            # Extract image
            image_url = poi_data.get('image') or poi_data.get('photo') or poi_data.get('thumbnail')
            if isinstance(image_url, dict):
                image_url = image_url.get('url') or image_url.get('src')

            # Extract images array
            images = poi_data.get('images') or poi_data.get('photos') or []
            if not isinstance(images, list):
                images = [images] if images else []

            # Extract description
            description = poi_data.get('description', '')

            # Extract phone
            phone = poi_data.get('phone') or poi_data.get('telephone')

            # Extract website
            website = poi_data.get('website') or poi_data.get('web')

            # Extract ranking
            ranking = poi_data.get('ranking') or poi_data.get('rankingString')

            # Extract amenities
            amenities = poi_data.get('amenities') or poi_data.get('features') or []

            # Extract awards
            awards = poi_data.get('awards') or []

            # Extract hours
            hours = poi_data.get('hours') or poi_data.get('openingHours')

            return {
                'tripadvisor_id': location_id,
                'name': name,
                'category': category,
                'subcategory': subcategory,
                'description': description,
                'url': url,
                'rating': rating,
                'rating_count': rating_count,
                'ranking': ranking,
                'price_level': price_level,
                'price_range': price_range,
                'address': address,
                'city': poi_city,
                'country': poi_country,
                'country_code': self._get_country_code(country_slug),
                'latitude': latitude,
                'longitude': longitude,
                'phone': phone,
                'website': website,
                'email': poi_data.get('email'),
                'hours': hours,
                'amenities': amenities if amenities else None,
                'cuisine_types': cuisine_types,
                'hotel_class': hotel_class,
                'image_url': image_url,
                'images': images if images else None,
                'awards': awards if awards else None,
                'raw_data': poi_data,
                'scraped_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }

        except Exception as e:
            self.log(f"Error creating POI record: {str(e)}", level="warning")
            return None

    def _get_country_code(self, country_slug: str) -> str:
        """Get ISO country code from slug"""
        country_codes = {
            "austria": "AT", "belgium": "BE", "croatia": "HR", "czech-republic": "CZ",
            "denmark": "DK", "finland": "FI", "france": "FR", "germany": "DE",
            "greece": "GR", "hungary": "HU", "iceland": "IS", "ireland": "IE",
            "italy": "IT", "netherlands": "NL", "norway": "NO", "poland": "PL",
            "portugal": "PT", "romania": "RO", "spain": "ES", "sweden": "SE",
            "switzerland": "CH", "turkey": "TR", "united-kingdom": "GB",
        }
        return country_codes.get(country_slug, "")

    async def _fetch_reviews(self, location_id: str, poi_url: str, max_reviews: int) -> List[Dict]:
        """Fetch reviews for a POI"""
        reviews = []

        try:
            # Build reviews URL
            if poi_url:
                reviews_url = poi_url
            else:
                reviews_url = f"{self.BASE_URL}/ShowUserReviews-g0-d{location_id}"

            response = await self.http_client.get(
                reviews_url,
                headers=self.DEFAULT_HEADERS,
                cookies=self.session_cookies,
                follow_redirects=True,
                timeout=30.0
            )

            if response.status_code == 200:
                reviews = self._extract_reviews_from_html(response.text, location_id, max_reviews)

        except Exception as e:
            self.log(f"Error fetching reviews for {location_id}: {str(e)}", level="warning")

        return reviews

    def _extract_reviews_from_html(self, html: str, poi_id: str, max_reviews: int) -> List[Dict]:
        """Extract reviews from HTML"""
        reviews = []

        try:
            # Look for JSON-LD review data
            json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

            for match in matches:
                try:
                    data = json.loads(match.strip())

                    # Look for reviews in aggregateRating or review array
                    review_list = data.get('review', [])
                    if isinstance(review_list, dict):
                        review_list = [review_list]

                    for review in review_list[:max_reviews]:
                        parsed = {
                            'review_id': str(review.get('id', hashlib.md5(str(review).encode()).hexdigest()[:12])),
                            'poi_id': poi_id,
                            'title': review.get('name', ''),
                            'text': review.get('reviewBody', ''),
                            'rating': review.get('reviewRating', {}).get('ratingValue'),
                            'published_date': review.get('datePublished'),
                            'reviewer_name': review.get('author', {}).get('name'),
                            'raw_data': review,
                        }
                        if parsed['text'] or parsed['title']:
                            reviews.append(parsed)

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.log(f"Error parsing reviews: {str(e)}", level="warning")

        return reviews

    async def _get_progress(self, country: str, city: str, category: str) -> int:
        """Get saved progress offset for resuming"""
        try:
            from app.core.database import engine
            from sqlalchemy import select

            tables = self.define_tables()
            progress_table = tables[2]

            async with engine.begin() as conn:
                await conn.run_sync(self.metadata.create_all)

                query = select(progress_table.c.offset).where(
                    progress_table.c.country == country,
                    progress_table.c.city == city,
                    progress_table.c.category == category,
                    progress_table.c.completed == 0
                ).order_by(progress_table.c.processed_at.desc()).limit(1)

                result = await conn.execute(query)
                row = result.fetchone()

                if row:
                    return row[0]

        except Exception as e:
            self.log(f"Error getting progress: {str(e)}", level="warning")

        return 0

    async def _save_progress(
        self,
        country: str,
        city: str,
        category: str,
        offset_or_total: int,
        completed: bool = False
    ):
        """Save scraping progress"""
        try:
            from app.core.database import engine
            from sqlalchemy import text

            tables = self.define_tables()
            progress_table = tables[2]

            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))
                await conn.run_sync(self.metadata.create_all)

                stmt = pg_insert(progress_table).values(
                    country=country,
                    city=city,
                    category=category,
                    offset=offset_or_total if not completed else 0,
                    total_found=offset_or_total if completed else None,
                    completed=1 if completed else 0,
                    processed_at=datetime.utcnow()
                )

                await conn.execute(stmt)

        except Exception as e:
            self.log(f"Error saving progress: {str(e)}", level="warning")

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Save scraped POIs to database"""
        if not results:
            self.log("No POIs to save")
            return

        self.log(f"Saving {len(results)} POIs to database...")

        try:
            from app.core.database import engine
            from sqlalchemy import text

            tables = self.define_tables()
            pois_table = tables[0]
            reviews_table = tables[1]

            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))
                await conn.run_sync(self.metadata.create_all)

                saved_count = 0
                reviews_count = 0

                for poi in results:
                    reviews = poi.pop('reviews', [])

                    stmt = pg_insert(pois_table).values(**poi)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['tripadvisor_id'],
                        set_={
                            'name': stmt.excluded.name,
                            'category': stmt.excluded.category,
                            'subcategory': stmt.excluded.subcategory,
                            'description': stmt.excluded.description,
                            'url': stmt.excluded.url,
                            'rating': stmt.excluded.rating,
                            'rating_count': stmt.excluded.rating_count,
                            'ranking': stmt.excluded.ranking,
                            'price_level': stmt.excluded.price_level,
                            'price_range': stmt.excluded.price_range,
                            'address': stmt.excluded.address,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'phone': stmt.excluded.phone,
                            'website': stmt.excluded.website,
                            'hours': stmt.excluded.hours,
                            'amenities': stmt.excluded.amenities,
                            'cuisine_types': stmt.excluded.cuisine_types,
                            'hotel_class': stmt.excluded.hotel_class,
                            'image_url': stmt.excluded.image_url,
                            'images': stmt.excluded.images,
                            'awards': stmt.excluded.awards,
                            'raw_data': stmt.excluded.raw_data,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    await conn.execute(stmt)
                    saved_count += 1

                    for review in reviews:
                        if review.get('review_id'):
                            review_stmt = pg_insert(reviews_table).values(**review)
                            review_stmt = review_stmt.on_conflict_do_update(
                                index_elements=['review_id'],
                                set_={
                                    'title': review_stmt.excluded.title,
                                    'text': review_stmt.excluded.text,
                                    'rating': review_stmt.excluded.rating,
                                    'helpful_votes': review_stmt.excluded.helpful_votes,
                                    'raw_data': review_stmt.excluded.raw_data,
                                }
                            )
                            await conn.execute(review_stmt)
                            reviews_count += 1

                self.log(f"Successfully saved {saved_count} POIs and {reviews_count} reviews to database")

        except Exception as e:
            self.log(f"Error saving to database: {str(e)}", level="error")
            raise


# Main function for testing
async def main():
    """Test the scraper"""
    import httpx

    # Create a test scraper
    class TestTripAdvisorScraper(TripAdvisorScraper):
        def __init__(self):
            self.scraper_id = 999
            self.schema_name = "scraper_test"
            self.config = {}
            self.min_delay = 2.0
            self.max_delay = 5.0
            self.request_count = 0
            self.session_cookies = {}
            self._logs = []
            self.http_client = httpx.AsyncClient()
            self.metadata = None

        def log(self, message: str, level: str = "info"):
            print(f"[{level.upper()}] {message}")
            self._logs.append(f"[{level.upper()}] {message}")

        def get_logs(self) -> str:
            return "\n".join(self._logs)

        async def report_progress(self, count: int, message: str):
            print(f"Progress: {count} - {message}")

        async def cleanup(self):
            await self.http_client.aclose()

    scraper = TestTripAdvisorScraper()

    try:
        # Test GraphQL location search
        print("\n" + "="*80)
        print("Testing GraphQL location search...")
        print("="*80)

        await scraper._init_session()
        geo_id = await scraper._search_location_graphql("Brussels", "Belgium")
        print(f"Brussels geo_id: {geo_id}")

        # Test fetching attractions
        print("\n" + "="*80)
        print("Testing attractions fetch...")
        print("="*80)

        if geo_id:
            pois = await scraper._fetch_pois_from_page(
                city="Brussels",
                country="Belgium",
                category="attractions",
                geo_id=geo_id,
                offset=0
            )

            print(f"\nFound {len(pois)} attractions")

            for i, poi in enumerate(pois[:5], 1):
                print(f"\n{i}. {poi.get('name', 'N/A')}")
                print(f"   ID: {poi.get('locationId', 'N/A')}")
                print(f"   Rating: {poi.get('rating', 'N/A')}")
                print(f"   Reviews: {poi.get('reviewCount', 'N/A')}")
                print(f"   Lat/Lng: {poi.get('latitude', 'N/A')}, {poi.get('longitude', 'N/A')}")
                print(f"   URL: {poi.get('url', 'N/A')[:80]}...")

    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

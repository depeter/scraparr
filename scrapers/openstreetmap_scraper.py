#!/usr/bin/env python3
"""
OpenStreetMap POI Scraper for Scraparr
Uses the Overpass API to fetch tourism POIs (attractions, museums, monuments, etc.)

This is a one-time scraper for static POI data - monuments, museums, castles, etc.
don't change often, so this only needs to run once or occasionally for updates.

Features:
- Uses free Overpass API (no authentication required)
- Fetches tourism and historic POIs with coordinates
- Supports country-by-country or region-based scraping
- No CAPTCHA or blocking issues
"""

import sys
sys.path.insert(0, '/app/backend')

from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List, Optional
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Text, JSON, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
import json
from datetime import datetime


# European countries with ISO codes and bounding boxes (south, west, north, east)
EUROPEAN_COUNTRIES = {
    "austria": {"name": "Austria", "iso": "AT", "bbox": [46.3, 9.5, 49.0, 17.2]},
    "belgium": {"name": "Belgium", "iso": "BE", "bbox": [49.5, 2.5, 51.5, 6.4]},
    "croatia": {"name": "Croatia", "iso": "HR", "bbox": [42.4, 13.5, 46.6, 19.5]},
    "czech-republic": {"name": "Czech Republic", "iso": "CZ", "bbox": [48.5, 12.1, 51.1, 18.9]},
    "denmark": {"name": "Denmark", "iso": "DK", "bbox": [54.5, 8.0, 57.8, 15.2]},
    "finland": {"name": "Finland", "iso": "FI", "bbox": [59.8, 20.5, 70.1, 31.6]},
    "france": {"name": "France", "iso": "FR", "bbox": [41.3, -5.2, 51.1, 9.6]},
    "germany": {"name": "Germany", "iso": "DE", "bbox": [47.3, 5.9, 55.1, 15.0]},
    "greece": {"name": "Greece", "iso": "GR", "bbox": [34.8, 19.4, 41.8, 29.6]},
    "hungary": {"name": "Hungary", "iso": "HU", "bbox": [45.7, 16.1, 48.6, 22.9]},
    "iceland": {"name": "Iceland", "iso": "IS", "bbox": [63.3, -24.5, 66.5, -13.5]},
    "ireland": {"name": "Ireland", "iso": "IE", "bbox": [51.4, -10.5, 55.4, -6.0]},
    "italy": {"name": "Italy", "iso": "IT", "bbox": [35.5, 6.6, 47.1, 18.5]},
    "netherlands": {"name": "Netherlands", "iso": "NL", "bbox": [50.8, 3.4, 53.5, 7.2]},
    "norway": {"name": "Norway", "iso": "NO", "bbox": [58.0, 4.6, 71.2, 31.1]},
    "poland": {"name": "Poland", "iso": "PL", "bbox": [49.0, 14.1, 54.8, 24.2]},
    "portugal": {"name": "Portugal", "iso": "PT", "bbox": [36.9, -9.5, 42.2, -6.2]},
    "romania": {"name": "Romania", "iso": "RO", "bbox": [43.6, 20.3, 48.3, 29.7]},
    "spain": {"name": "Spain", "iso": "ES", "bbox": [36.0, -9.3, 43.8, 4.3]},
    "sweden": {"name": "Sweden", "iso": "SE", "bbox": [55.3, 11.1, 69.1, 24.2]},
    "switzerland": {"name": "Switzerland", "iso": "CH", "bbox": [45.8, 6.0, 47.8, 10.5]},
    "turkey": {"name": "Turkey", "iso": "TR", "bbox": [35.8, 26.0, 42.1, 44.8]},
    "united-kingdom": {"name": "United Kingdom", "iso": "GB", "bbox": [49.9, -8.6, 60.9, 1.8]},
    "luxembourg": {"name": "Luxembourg", "iso": "LU", "bbox": [49.4, 5.7, 50.2, 6.5]},
    "slovenia": {"name": "Slovenia", "iso": "SI", "bbox": [45.4, 13.4, 46.9, 16.6]},
    "slovakia": {"name": "Slovakia", "iso": "SK", "bbox": [47.7, 16.8, 49.6, 22.6]},
    "estonia": {"name": "Estonia", "iso": "EE", "bbox": [57.5, 21.8, 59.7, 28.2]},
    "latvia": {"name": "Latvia", "iso": "LV", "bbox": [55.7, 20.9, 58.1, 28.2]},
    "lithuania": {"name": "Lithuania", "iso": "LT", "bbox": [53.9, 21.0, 56.5, 26.8]},
    "bulgaria": {"name": "Bulgaria", "iso": "BG", "bbox": [41.2, 22.4, 44.2, 28.6]},
    "malta": {"name": "Malta", "iso": "MT", "bbox": [35.8, 14.2, 36.1, 14.6]},
    "cyprus": {"name": "Cyprus", "iso": "CY", "bbox": [34.6, 32.3, 35.7, 34.6]},
}

# POI types to fetch from OpenStreetMap
POI_TYPES = {
    # Tourism tags
    "tourism": [
        "attraction",
        "museum",
        "gallery",
        "artwork",
        "viewpoint",
        "zoo",
        "aquarium",
        "theme_park",
        "information",
    ],
    # Historic tags
    "historic": [
        "monument",
        "memorial",
        "castle",
        "ruins",
        "archaeological_site",
        "battlefield",
        "fort",
        "manor",
        "palace",
        "church",
        "cathedral",
        "monastery",
        "tomb",
        "wayside_cross",
        "wayside_shrine",
    ],
    # Amenity tags (cultural)
    "amenity": [
        "theatre",
        "cinema",
        "arts_centre",
        "library",
        "place_of_worship",
    ],
    # Leisure tags
    "leisure": [
        "park",
        "garden",
        "nature_reserve",
        "stadium",
    ],
}


class OpenStreetMapScraper(BaseScraper):
    """
    Scraper for OpenStreetMap POIs using Overpass API

    This scraper fetches tourism-related Points of Interest from OpenStreetMap.
    It uses the Overpass API which is free and doesn't require authentication.

    POI data includes:
    - Coordinates (latitude/longitude)
    - Name and description
    - Category (museum, monument, castle, etc.)
    - Website, phone, opening hours
    - Wikipedia/Wikidata links
    """

    scraper_type = ScraperType.API

    # Overpass API endpoints (use multiple for load balancing)
    OVERPASS_ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_endpoint_index = 0
        self.min_delay = 2.0
        self.max_delay = 5.0

    def define_tables(self) -> List[Table]:
        """Define database tables for OpenStreetMap POI data"""

        pois_table = Table(
            'pois',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('osm_id', String(100), unique=True, nullable=False),  # node/123456 or way/789
            Column('osm_type', String(50)),  # node, way, relation
            Column('name', String(500)),
            Column('name_en', String(500)),  # English name if available
            Column('category', String(50)),  # tourism, historic, amenity, leisure
            Column('subcategory', String(100)),  # museum, monument, castle, etc.
            Column('description', Text),
            Column('latitude', Float, nullable=False),
            Column('longitude', Float, nullable=False),
            Column('address', String(500)),
            Column('city', String(255)),
            Column('country', String(100)),
            Column('country_code', String(5)),
            Column('postcode', String(100)),  # Can be multiple postcodes separated by semicolons
            Column('phone', String(100)),
            Column('website', String(1000)),
            Column('email', String(255)),
            Column('opening_hours', String(1000)),  # Can be very detailed schedules
            Column('wheelchair', String(50)),
            Column('wikipedia', String(500)),  # Wikipedia article link
            Column('wikidata', String(50)),  # Wikidata ID (Q12345)
            Column('image', String(1000)),  # Image URL if available
            Column('heritage', String(255)),  # Heritage designation
            Column('architect', String(255)),
            Column('start_date', String(255)),  # Year built/founded (can be long descriptions)
            Column('tags', JSON),  # All OSM tags as JSON
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        scrape_progress_table = Table(
            'scrape_progress',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('country', String(100)),
            Column('poi_type', String(50)),
            Column('pois_found', Integer, default=0),
            Column('completed', Integer, default=0),
            Column('processed_at', DateTime, default=func.now()),
            extend_existing=True,
            schema=self.schema_name
        )

        return [pois_table, scrape_progress_table]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape OpenStreetMap for POIs

        Params:
            country: Country slug (e.g., "belgium", "france") or "all" for all Europe
            poi_types: List of POI types to fetch (default: all tourism + historic)
            min_delay: Minimum delay between API calls (default: 2.0)
            max_delay: Maximum delay between API calls (default: 5.0)
        """
        country_param = params.get('country', 'belgium')
        poi_types_param = params.get('poi_types', None)  # None = all types
        self.min_delay = params.get('min_delay', 2.0)
        self.max_delay = params.get('max_delay', 5.0)

        self.log(f"Starting OpenStreetMap POI scrape")
        self.log(f"Country: {country_param}")
        self.log(f"Rate limiting: {self.min_delay}s - {self.max_delay}s delay between requests")

        # Determine countries to scrape
        countries_to_scrape = []
        if country_param.lower() == 'all':
            countries_to_scrape = list(EUROPEAN_COUNTRIES.keys())
            self.log(f"Scraping all {len(countries_to_scrape)} European countries")
        elif country_param.lower() in EUROPEAN_COUNTRIES:
            countries_to_scrape = [country_param.lower()]
        else:
            self.log(f"Unknown country: {country_param}", level="error")
            raise ValueError(f"Unknown country: {country_param}")

        # Determine POI types to fetch
        if poi_types_param:
            poi_types = {k: v for k, v in POI_TYPES.items() if k in poi_types_param}
        else:
            poi_types = POI_TYPES

        all_pois = []
        seen_ids = set()

        for country_slug in countries_to_scrape:
            country_info = EUROPEAN_COUNTRIES[country_slug]
            country_name = country_info['name']
            bbox = country_info['bbox']

            self.log(f"\n{'='*60}")
            self.log(f"Scraping {country_name}")
            self.log(f"Bounding box: {bbox}")
            self.log(f"{'='*60}")

            for category, subcategories in poi_types.items():
                for subcategory in subcategories:
                    self.log(f"\nFetching {category}={subcategory} in {country_name}...")

                    try:
                        pois = await self._fetch_pois(
                            bbox=bbox,
                            category=category,
                            subcategory=subcategory,
                            country_name=country_name,
                            country_code=country_info['iso'],
                            seen_ids=seen_ids
                        )

                        all_pois.extend(pois)
                        self.log(f"Found {len(pois)} {category}={subcategory} POIs")

                        # Save progress
                        await self._save_progress(country_slug, f"{category}={subcategory}", len(pois))

                    except Exception as e:
                        self.log(f"Error fetching {category}={subcategory}: {str(e)}", level="error")
                        continue

                    await self.report_progress(
                        len(all_pois),
                        f"Scraped {len(all_pois)} POIs. Last: {subcategory} in {country_name}"
                    )

        self.log(f"\n{'='*60}")
        self.log(f"Scraping complete! Total unique POIs: {len(all_pois)}")
        self.log(f"{'='*60}")

        return all_pois

    async def _fetch_pois(
        self,
        bbox: List[float],
        category: str,
        subcategory: str,
        country_name: str,
        country_code: str,
        seen_ids: set
    ) -> List[Dict[str, Any]]:
        """Fetch POIs from Overpass API"""

        # Build Overpass QL query
        south, west, north, east = bbox
        query = f"""
        [out:json][timeout:180];
        (
            node["{category}"="{subcategory}"]({south},{west},{north},{east});
            way["{category}"="{subcategory}"]({south},{west},{north},{east});
            relation["{category}"="{subcategory}"]({south},{west},{north},{east});
        );
        out center tags;
        """

        # Apply rate limiting
        import random
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

        # Try endpoints in rotation
        endpoint = self.OVERPASS_ENDPOINTS[self.current_endpoint_index]
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.OVERPASS_ENDPOINTS)

        try:
            response = await self.http_client.post(
                endpoint,
                data={"data": query},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Scraparr/1.0 (tourism POI collection)",
                },
                timeout=200.0
            )

            if response.status_code == 429:
                self.log("Rate limited, waiting 60 seconds...", level="warning")
                await asyncio.sleep(60)
                return await self._fetch_pois(bbox, category, subcategory, country_name, country_code, seen_ids)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code} from Overpass API", level="error")
                return []

            data = response.json()
            elements = data.get('elements', [])

            pois = []
            for element in elements:
                osm_id = f"{element['type']}/{element['id']}"

                if osm_id in seen_ids:
                    continue
                seen_ids.add(osm_id)

                poi = self._parse_element(element, category, subcategory, country_name, country_code)
                if poi:
                    pois.append(poi)

            return pois

        except Exception as e:
            self.log(f"Error querying Overpass API: {str(e)}", level="error")
            return []

    def _parse_element(
        self,
        element: Dict,
        category: str,
        subcategory: str,
        country_name: str,
        country_code: str
    ) -> Optional[Dict[str, Any]]:
        """Parse an OSM element into POI format"""

        try:
            tags = element.get('tags', {})

            # Get coordinates
            if element['type'] == 'node':
                lat = element.get('lat')
                lon = element.get('lon')
            else:
                # For ways and relations, use the center point
                center = element.get('center', {})
                lat = center.get('lat')
                lon = center.get('lon')

            if not lat or not lon:
                return None

            # Get name (prefer English, fallback to local name)
            name = tags.get('name:en') or tags.get('name') or tags.get('int_name')
            name_en = tags.get('name:en')

            # Build address
            address_parts = []
            if tags.get('addr:street'):
                addr = tags.get('addr:housenumber', '')
                if addr:
                    address_parts.append(f"{addr} {tags['addr:street']}")
                else:
                    address_parts.append(tags['addr:street'])
            if tags.get('addr:city'):
                address_parts.append(tags['addr:city'])
            address = ', '.join(address_parts) if address_parts else None

            # Get city
            city = tags.get('addr:city') or tags.get('is_in:city')

            # Get description
            description = tags.get('description:en') or tags.get('description')

            # Get Wikipedia/Wikidata
            wikipedia = tags.get('wikipedia')
            wikidata = tags.get('wikidata')

            # If we have a Wikipedia tag, convert to full URL
            wikipedia_url = None
            if wikipedia:
                parts = wikipedia.split(':', 1)
                if len(parts) == 2:
                    lang, article = parts
                    wikipedia_url = f"https://{lang}.wikipedia.org/wiki/{article.replace(' ', '_')}"
                else:
                    wikipedia_url = f"https://en.wikipedia.org/wiki/{wikipedia.replace(' ', '_')}"

            # Get image (Wikimedia Commons)
            image = tags.get('image') or tags.get('wikimedia_commons')
            if image and image.startswith('File:'):
                # Convert to Wikimedia Commons URL
                image = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image[5:].replace(' ', '_')}"

            return {
                'osm_id': f"{element['type']}/{element['id']}",
                'osm_type': element['type'],
                'name': name,
                'name_en': name_en,
                'category': category,
                'subcategory': subcategory,
                'description': description,
                'latitude': lat,
                'longitude': lon,
                'address': address,
                'city': city,
                'country': country_name,
                'country_code': country_code,
                'postcode': tags.get('addr:postcode'),
                'phone': tags.get('phone') or tags.get('contact:phone'),
                'website': tags.get('website') or tags.get('contact:website') or tags.get('url'),
                'email': tags.get('email') or tags.get('contact:email'),
                'opening_hours': tags.get('opening_hours'),
                'wheelchair': tags.get('wheelchair'),
                'wikipedia': wikipedia_url,
                'wikidata': wikidata,
                'image': image,
                'heritage': tags.get('heritage') or tags.get('heritage:operator'),
                'architect': tags.get('architect'),
                'start_date': tags.get('start_date') or tags.get('year_of_construction'),
                'tags': tags,
                'scraped_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }

        except Exception as e:
            self.log(f"Error parsing element: {str(e)}", level="warning")
            return None

    async def _save_progress(self, country: str, poi_type: str, count: int):
        """Save scraping progress"""
        try:
            from app.core.database import engine
            from sqlalchemy import text

            tables = self.define_tables()
            progress_table = tables[1]

            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))
                await conn.run_sync(self.metadata.create_all)

                stmt = pg_insert(progress_table).values(
                    country=country,
                    poi_type=poi_type,
                    pois_found=count,
                    completed=1,
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

            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))
                await conn.run_sync(self.metadata.create_all)

                saved_count = 0

                for poi in results:
                    stmt = pg_insert(pois_table).values(**poi)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['osm_id'],
                        set_={
                            'name': stmt.excluded.name,
                            'name_en': stmt.excluded.name_en,
                            'category': stmt.excluded.category,
                            'subcategory': stmt.excluded.subcategory,
                            'description': stmt.excluded.description,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'address': stmt.excluded.address,
                            'city': stmt.excluded.city,
                            'phone': stmt.excluded.phone,
                            'website': stmt.excluded.website,
                            'email': stmt.excluded.email,
                            'opening_hours': stmt.excluded.opening_hours,
                            'wheelchair': stmt.excluded.wheelchair,
                            'wikipedia': stmt.excluded.wikipedia,
                            'wikidata': stmt.excluded.wikidata,
                            'image': stmt.excluded.image,
                            'heritage': stmt.excluded.heritage,
                            'tags': stmt.excluded.tags,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    await conn.execute(stmt)
                    saved_count += 1

                self.log(f"Successfully saved {saved_count} POIs to database")

        except Exception as e:
            self.log(f"Error saving to database: {str(e)}", level="error")
            raise


# Standalone test
async def main():
    """Test the scraper standalone"""
    import httpx

    class TestOSMScraper:
        def __init__(self):
            self.http_client = httpx.AsyncClient()
            self.min_delay = 1.0
            self.max_delay = 2.0
            self.current_endpoint_index = 0
            self.OVERPASS_ENDPOINTS = [
                "https://overpass-api.de/api/interpreter",
            ]

        def log(self, msg, level="info"):
            print(f"[{level.upper()}] {msg}")

        async def cleanup(self):
            await self.http_client.aclose()

    scraper = TestOSMScraper()

    # Test query for Belgium museums
    bbox = EUROPEAN_COUNTRIES['belgium']['bbox']
    south, west, north, east = bbox

    query = f"""
    [out:json][timeout:60];
    (
        node["tourism"="museum"]({south},{west},{north},{east});
        way["tourism"="museum"]({south},{west},{north},{east});
    );
    out center tags;
    """

    print(f"Testing Overpass API for Belgium museums...")
    print(f"Bbox: {bbox}")

    try:
        response = await scraper.http_client.post(
            scraper.OVERPASS_ENDPOINTS[0],
            data={"data": query},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            print(f"Found {len(elements)} museums in Belgium")

            for elem in elements[:5]:
                tags = elem.get('tags', {})
                name = tags.get('name', 'Unnamed')
                lat = elem.get('lat') or elem.get('center', {}).get('lat')
                lon = elem.get('lon') or elem.get('center', {}).get('lon')
                website = tags.get('website', 'N/A')
                print(f"  - {name}")
                print(f"    Coords: {lat}, {lon}")
                print(f"    Website: {website[:50]}..." if len(str(website)) > 50 else f"    Website: {website}")

    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

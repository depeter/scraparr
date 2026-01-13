#!/usr/bin/env python3
"""
Wikidata Tourist Attractions Scraper for Scraparr
Uses SPARQL queries to fetch tourist attractions, monuments, museums, etc.

Wikidata provides rich structured data including:
- Coordinates
- Descriptions in multiple languages
- Wikipedia links
- Images from Wikimedia Commons
- Heritage designations
- Opening dates, architects, etc.

This is a one-time scraper for static POI data.
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
from urllib.parse import quote


# European countries with Wikidata IDs
EUROPEAN_COUNTRIES = {
    "austria": {"name": "Austria", "wikidata": "Q40"},
    "belgium": {"name": "Belgium", "wikidata": "Q31"},
    "croatia": {"name": "Croatia", "wikidata": "Q224"},
    "czech-republic": {"name": "Czech Republic", "wikidata": "Q213"},
    "denmark": {"name": "Denmark", "wikidata": "Q35"},
    "finland": {"name": "Finland", "wikidata": "Q33"},
    "france": {"name": "France", "wikidata": "Q142"},
    "germany": {"name": "Germany", "wikidata": "Q183"},
    "greece": {"name": "Greece", "wikidata": "Q41"},
    "hungary": {"name": "Hungary", "wikidata": "Q28"},
    "iceland": {"name": "Iceland", "wikidata": "Q189"},
    "ireland": {"name": "Ireland", "wikidata": "Q27"},
    "italy": {"name": "Italy", "wikidata": "Q38"},
    "netherlands": {"name": "Netherlands", "wikidata": "Q55"},
    "norway": {"name": "Norway", "wikidata": "Q20"},
    "poland": {"name": "Poland", "wikidata": "Q36"},
    "portugal": {"name": "Portugal", "wikidata": "Q45"},
    "romania": {"name": "Romania", "wikidata": "Q218"},
    "spain": {"name": "Spain", "wikidata": "Q29"},
    "sweden": {"name": "Sweden", "wikidata": "Q34"},
    "switzerland": {"name": "Switzerland", "wikidata": "Q39"},
    "turkey": {"name": "Turkey", "wikidata": "Q43"},
    "united-kingdom": {"name": "United Kingdom", "wikidata": "Q145"},
    "luxembourg": {"name": "Luxembourg", "wikidata": "Q32"},
    "slovenia": {"name": "Slovenia", "wikidata": "Q215"},
    "slovakia": {"name": "Slovakia", "wikidata": "Q214"},
    "estonia": {"name": "Estonia", "wikidata": "Q191"},
    "latvia": {"name": "Latvia", "wikidata": "Q211"},
    "lithuania": {"name": "Lithuania", "wikidata": "Q37"},
    "bulgaria": {"name": "Bulgaria", "wikidata": "Q219"},
    "malta": {"name": "Malta", "wikidata": "Q233"},
    "cyprus": {"name": "Cyprus", "wikidata": "Q229"},
}

# POI types with their Wikidata class IDs
# These are "instance of" (P31) or "subclass of" (P279) relationships
POI_TYPES = {
    "tourist_attraction": "Q570116",  # tourist attraction
    "museum": "Q33506",  # museum
    "art_museum": "Q207694",  # art museum
    "castle": "Q23413",  # castle
    "palace": "Q16560",  # palace
    "monument": "Q4989906",  # monument
    "memorial": "Q5003624",  # memorial
    "church": "Q16970",  # church building
    "cathedral": "Q2977",  # cathedral
    "monastery": "Q44613",  # monastery
    "archaeological_site": "Q839954",  # archaeological site
    "historic_site": "Q839954",  # historic site
    "world_heritage_site": "Q9259",  # World Heritage Site
    "national_park": "Q46169",  # national park
    "zoo": "Q43501",  # zoo
    "botanical_garden": "Q167346",  # botanical garden
    "aquarium": "Q2281788",  # public aquarium
    "theatre": "Q24354",  # theatre
    "opera_house": "Q153562",  # opera house
    "concert_hall": "Q1060829",  # concert hall
    "lighthouse": "Q39715",  # lighthouse
    "bridge": "Q12280",  # bridge (famous ones)
    "tower": "Q12518",  # tower
    "statue": "Q179700",  # statue
    "fountain": "Q483453",  # fountain
}


class WikidataScraper(BaseScraper):
    """
    Scraper for Wikidata tourist attractions using SPARQL

    This scraper queries Wikidata's SPARQL endpoint to fetch structured
    data about tourist attractions, museums, monuments, and other POIs.

    Features:
    - Rich structured data (descriptions, images, links)
    - Multi-language support
    - Wikipedia article links
    - Wikimedia Commons images
    - Heritage and UNESCO designations
    """

    scraper_type = ScraperType.API

    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_delay = 2.0
        self.max_delay = 5.0

    def define_tables(self) -> List[Table]:
        """Define database tables for Wikidata POI data"""

        pois_table = Table(
            'pois',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('wikidata_id', String(20), unique=True, nullable=False),  # Q12345
            Column('name', String(500)),
            Column('name_en', String(500)),
            Column('description', Text),
            Column('description_en', Text),
            Column('poi_type', String(100)),  # museum, castle, monument, etc.
            Column('latitude', Float),
            Column('longitude', Float),
            Column('country', String(100)),
            Column('country_code', String(5)),
            Column('city', String(255)),
            Column('address', String(500)),
            Column('inception', String(50)),  # Year founded/built
            Column('architect', String(255)),
            Column('architectural_style', String(255)),
            Column('heritage_status', String(255)),  # UNESCO, national monument, etc.
            Column('visitors_per_year', Integer),
            Column('official_website', String(1000)),
            Column('wikipedia_en', String(500)),
            Column('wikipedia_local', String(500)),
            Column('image_url', String(1000)),  # Wikimedia Commons image
            Column('commons_category', String(255)),  # Wikimedia Commons category
            Column('opening_hours', String(255)),
            Column('phone', String(100)),
            Column('email', String(255)),
            Column('raw_data', JSON),
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
        Scrape Wikidata for tourist attractions

        Params:
            country: Country slug or "all" for all Europe
            poi_types: List of POI types to fetch (default: all)
            min_delay: Minimum delay between API calls (default: 2.0)
            max_delay: Maximum delay between API calls (default: 5.0)
        """
        country_param = params.get('country', 'belgium')
        poi_types_param = params.get('poi_types', None)
        self.min_delay = params.get('min_delay', 2.0)
        self.max_delay = params.get('max_delay', 5.0)

        self.log(f"Starting Wikidata POI scrape")
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
            country_wikidata = country_info['wikidata']

            self.log(f"\n{'='*60}")
            self.log(f"Scraping {country_name} ({country_wikidata})")
            self.log(f"{'='*60}")

            for poi_type_name, poi_type_id in poi_types.items():
                self.log(f"\nFetching {poi_type_name} in {country_name}...")

                try:
                    pois = await self._fetch_pois(
                        country_wikidata=country_wikidata,
                        country_name=country_name,
                        poi_type_name=poi_type_name,
                        poi_type_id=poi_type_id,
                        seen_ids=seen_ids
                    )

                    all_pois.extend(pois)
                    self.log(f"Found {len(pois)} {poi_type_name}")

                    await self._save_progress(country_slug, poi_type_name, len(pois))

                except Exception as e:
                    self.log(f"Error fetching {poi_type_name}: {str(e)}", level="error")
                    import traceback
                    self.log(f"Traceback: {traceback.format_exc()}", level="error")
                    continue

                await self.report_progress(
                    len(all_pois),
                    f"Scraped {len(all_pois)} POIs. Last: {poi_type_name} in {country_name}"
                )

        self.log(f"\n{'='*60}")
        self.log(f"Scraping complete! Total unique POIs: {len(all_pois)}")
        self.log(f"{'='*60}")

        return all_pois

    async def _fetch_pois(
        self,
        country_wikidata: str,
        country_name: str,
        poi_type_name: str,
        poi_type_id: str,
        seen_ids: set
    ) -> List[Dict[str, Any]]:
        """Fetch POIs from Wikidata SPARQL endpoint"""

        # SPARQL query for POIs in a country
        query = f"""
        SELECT DISTINCT
            ?item
            ?itemLabel
            ?itemDescription
            ?coord
            ?image
            ?website
            ?wikipedia
            ?inception
            ?architect ?architectLabel
            ?heritage ?heritageLabel
            ?visitors
            ?city ?cityLabel
            ?commons
        WHERE {{
            ?item wdt:P31/wdt:P279* wd:{poi_type_id} .
            ?item wdt:P17 wd:{country_wikidata} .
            ?item wdt:P625 ?coord .

            OPTIONAL {{ ?item wdt:P18 ?image . }}
            OPTIONAL {{ ?item wdt:P856 ?website . }}
            OPTIONAL {{ ?item wdt:P571 ?inception . }}
            OPTIONAL {{ ?item wdt:P84 ?architect . }}
            OPTIONAL {{ ?item wdt:P1435 ?heritage . }}
            OPTIONAL {{ ?item wdt:P1174 ?visitors . }}
            OPTIONAL {{ ?item wdt:P131 ?city . }}
            OPTIONAL {{ ?item wdt:P373 ?commons . }}

            OPTIONAL {{
                ?wikipedia schema:about ?item ;
                           schema:isPartOf <https://en.wikipedia.org/> .
            }}

            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,de,fr,nl,es,it" . }}
        }}
        LIMIT 5000
        """

        # Apply rate limiting
        import random
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

        try:
            headers = {
                "Accept": "application/sparql-results+json",
                "User-Agent": "Scraparr/1.0 (tourism POI collection; contact@example.com)",
            }

            response = await self.http_client.get(
                self.SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=headers,
                timeout=120.0
            )

            if response.status_code == 429:
                self.log("Rate limited, waiting 60 seconds...", level="warning")
                await asyncio.sleep(60)
                return await self._fetch_pois(country_wikidata, country_name, poi_type_name, poi_type_id, seen_ids)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code} from Wikidata", level="error")
                self.log(f"Response: {response.text[:500]}", level="error")
                return []

            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])

            pois = []
            for binding in bindings:
                wikidata_id = binding.get('item', {}).get('value', '').split('/')[-1]

                if wikidata_id in seen_ids:
                    continue
                seen_ids.add(wikidata_id)

                poi = self._parse_binding(binding, poi_type_name, country_name)
                if poi:
                    pois.append(poi)

            return pois

        except Exception as e:
            self.log(f"Error querying Wikidata: {str(e)}", level="error")
            return []

    def _parse_binding(self, binding: Dict, poi_type: str, country_name: str) -> Optional[Dict[str, Any]]:
        """Parse a SPARQL result binding into POI format"""

        try:
            # Extract Wikidata ID
            item_uri = binding.get('item', {}).get('value', '')
            wikidata_id = item_uri.split('/')[-1] if item_uri else None

            if not wikidata_id:
                return None

            # Extract name and description
            name = binding.get('itemLabel', {}).get('value', '')
            description = binding.get('itemDescription', {}).get('value', '')

            # Skip if name is just the Q-number (no label available)
            if name.startswith('Q') and name[1:].isdigit():
                name = None

            # Extract coordinates
            coord = binding.get('coord', {}).get('value', '')
            latitude = None
            longitude = None
            if coord:
                # Format: "Point(longitude latitude)"
                import re
                match = re.search(r'Point\(([-.0-9]+)\s+([-.0-9]+)\)', coord)
                if match:
                    longitude = float(match.group(1))
                    latitude = float(match.group(2))

            if not latitude or not longitude:
                return None

            # Extract image URL
            image_url = binding.get('image', {}).get('value', '')

            # Extract website
            website = binding.get('website', {}).get('value', '')

            # Extract Wikipedia URL
            wikipedia = binding.get('wikipedia', {}).get('value', '')

            # Extract inception (founding/construction date)
            inception = binding.get('inception', {}).get('value', '')
            if inception:
                # Extract just the year
                import re
                year_match = re.search(r'(\d{4})', inception)
                inception = year_match.group(1) if year_match else inception[:10]

            # Extract architect
            architect = binding.get('architectLabel', {}).get('value', '')

            # Extract heritage status
            heritage = binding.get('heritageLabel', {}).get('value', '')

            # Extract visitors per year
            visitors = binding.get('visitors', {}).get('value', '')
            visitors_int = None
            if visitors:
                try:
                    visitors_int = int(float(visitors))
                except (ValueError, TypeError):
                    pass

            # Extract city
            city = binding.get('cityLabel', {}).get('value', '')
            if city and city.startswith('Q') and city[1:].isdigit():
                city = None

            # Extract Commons category
            commons = binding.get('commons', {}).get('value', '')

            return {
                'wikidata_id': wikidata_id,
                'name': name,
                'name_en': name,  # Already in English from query
                'description': description,
                'description_en': description,
                'poi_type': poi_type,
                'latitude': latitude,
                'longitude': longitude,
                'country': country_name,
                'country_code': self._get_country_code(country_name),
                'city': city,
                'address': None,
                'inception': inception,
                'architect': architect,
                'architectural_style': None,
                'heritage_status': heritage,
                'visitors_per_year': visitors_int,
                'official_website': website,
                'wikipedia_en': wikipedia,
                'wikipedia_local': None,
                'image_url': image_url,
                'commons_category': commons,
                'opening_hours': None,
                'phone': None,
                'email': None,
                'raw_data': binding,
                'scraped_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }

        except Exception as e:
            return None

    def _get_country_code(self, country_name: str) -> str:
        """Get ISO country code from country name"""
        country_codes = {
            "Austria": "AT", "Belgium": "BE", "Croatia": "HR", "Czech Republic": "CZ",
            "Denmark": "DK", "Finland": "FI", "France": "FR", "Germany": "DE",
            "Greece": "GR", "Hungary": "HU", "Iceland": "IS", "Ireland": "IE",
            "Italy": "IT", "Netherlands": "NL", "Norway": "NO", "Poland": "PL",
            "Portugal": "PT", "Romania": "RO", "Spain": "ES", "Sweden": "SE",
            "Switzerland": "CH", "Turkey": "TR", "United Kingdom": "GB",
            "Luxembourg": "LU", "Slovenia": "SI", "Slovakia": "SK",
            "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT",
            "Bulgaria": "BG", "Malta": "MT", "Cyprus": "CY",
        }
        return country_codes.get(country_name, "")

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
                        index_elements=['wikidata_id'],
                        set_={
                            'name': stmt.excluded.name,
                            'name_en': stmt.excluded.name_en,
                            'description': stmt.excluded.description,
                            'description_en': stmt.excluded.description_en,
                            'poi_type': stmt.excluded.poi_type,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'city': stmt.excluded.city,
                            'inception': stmt.excluded.inception,
                            'architect': stmt.excluded.architect,
                            'heritage_status': stmt.excluded.heritage_status,
                            'visitors_per_year': stmt.excluded.visitors_per_year,
                            'official_website': stmt.excluded.official_website,
                            'wikipedia_en': stmt.excluded.wikipedia_en,
                            'image_url': stmt.excluded.image_url,
                            'commons_category': stmt.excluded.commons_category,
                            'raw_data': stmt.excluded.raw_data,
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
    import re

    async with httpx.AsyncClient() as client:
        # Test query for Belgian museums from Wikidata
        query = """
        SELECT DISTINCT
            ?item
            ?itemLabel
            ?itemDescription
            ?coord
            ?image
            ?website
            ?wikipedia
        WHERE {
            ?item wdt:P31/wdt:P279* wd:Q33506 .
            ?item wdt:P17 wd:Q31 .
            ?item wdt:P625 ?coord .

            OPTIONAL { ?item wdt:P18 ?image . }
            OPTIONAL { ?item wdt:P856 ?website . }

            OPTIONAL {
                ?wikipedia schema:about ?item ;
                           schema:isPartOf <https://en.wikipedia.org/> .
            }

            SERVICE wikibase:label { bd:serviceParam wikibase:language "en,nl,fr" . }
        }
        LIMIT 100
        """

        print("Testing Wikidata SPARQL for Belgian museums...")

        response = await client.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "Scraparr/1.0 (test)",
            },
            timeout=60.0
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            print(f"\nFound {len(bindings)} museums in Belgium from Wikidata!\n")

            for binding in bindings[:10]:
                item_uri = binding.get('item', {}).get('value', '')
                wikidata_id = item_uri.split('/')[-1]
                name = binding.get('itemLabel', {}).get('value', '')
                description = binding.get('itemDescription', {}).get('value', '')[:80]
                coord = binding.get('coord', {}).get('value', '')
                image = binding.get('image', {}).get('value', '')
                wikipedia = binding.get('wikipedia', {}).get('value', '')

                # Parse coordinates
                lat, lon = None, None
                if coord:
                    match = re.search(r'Point\(([-.0-9]+)\s+([-.0-9]+)\)', coord)
                    if match:
                        lon = float(match.group(1))
                        lat = float(match.group(2))

                print(f"  {name} ({wikidata_id})")
                print(f"    {description}...")
                print(f"    Coords: {lat:.5f}, {lon:.5f}" if lat else "    Coords: N/A")
                print(f"    Image: {'Yes' if image else 'No'} | Wikipedia: {'Yes' if wikipedia else 'No'}")
                print()


if __name__ == "__main__":
    asyncio.run(main())

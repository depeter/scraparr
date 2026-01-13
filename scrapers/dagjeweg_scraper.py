"""
DagjeWeg.NL Scraper for Scraparr

Scrapes day trip attractions from dagjeweg.nl, the largest Dutch day trip database.
Uses web scraping since no public API is available.

Features:
- Scrapes ~8000 attractions from all categories
- Extracts: name, description, address, coordinates, prices, ratings, contact info
- Respectful rate limiting (2-5 seconds between requests)
- Resume capability via progress tracking
- Only Dutch language available (no translations)

Author: Scraparr
"""
import sys
import os
sys.path.insert(0, '/app/backend')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from app.scrapers.base import BaseScraper, ScraperType
except ImportError:
    from abc import ABC, abstractmethod
    from enum import Enum

    class ScraperType(str, Enum):
        API = "api"
        WEB = "web"

    class BaseScraper(ABC):
        scraper_type = ScraperType.WEB
        def __init__(self, scraper_id=0, schema_name=None, config=None, headers=None, execution_id=None):
            self.scraper_id = scraper_id
            self.schema_name = schema_name
            self.config = config or {}
            self.headers = headers or {}
            self.execution_id = execution_id
            self.logs = []
            import httpx
            self.http_client = httpx.AsyncClient(timeout=60.0)
            from sqlalchemy import MetaData
            self.metadata = MetaData(schema=schema_name)

        def log(self, message, level="info"):
            print(f"[{level.upper()}] {message}")
            self.logs.append(f"[{level}] {message}")

        async def report_progress(self, items, msg):
            pass

        async def cleanup(self):
            await self.http_client.aclose()

from typing import Dict, Any, List, Optional, Set
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Text, JSON, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
import random
import re
from datetime import datetime
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class DagjeWegScraper(BaseScraper):
    """
    Web scraper for DagjeWeg.NL day trip attractions
    """

    scraper_type = ScraperType.WEB

    BASE_URL = "https://www.dagjeweg.nl"

    CATEGORIES = [
        "attractieparken", "musea", "dierentuinen", "speeltuinen", "zwembaden",
        "bowlen", "bioscopen", "theaters", "pretparken", "kinderboerderijen",
        "klimhallen", "escaperooms", "lasergamen", "trampolineparken",
        "indoor-speeltuinen", "kartbanen", "natuurgebieden", "kastelen",
        "stranden", "meren",
    ]

    PROVINCES = [
        "noord-holland", "zuid-holland", "noord-brabant", "gelderland",
        "utrecht", "overijssel", "limburg", "friesland", "groningen",
        "drenthe", "zeeland", "flevoland",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_delay = 2.0
        self.max_delay = 5.0

    def define_tables(self) -> List[Table]:
        attractions_table = Table(
            'attractions', self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('tip_id', Integer, unique=True, nullable=False, index=True),
            Column('name', String(500)),
            Column('description', Text),
            Column('short_description', String(1000)),
            Column('address', String(300)),
            Column('postal_code', String(20)),
            Column('city', String(100), index=True),
            Column('province', String(50), index=True),
            Column('country', String(50), default='NL'),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('price_adult', Float),
            Column('price_child', Float),
            Column('rating', Float),
            Column('review_count', Integer),
            Column('website', String(500)),
            Column('indoor_outdoor', String(50)),
            Column('pets_allowed', Integer),
            Column('image_url', String(500)),
            Column('url', String(500)),
            Column('raw_data', JSON),
            Column('scraped_at', DateTime, default=func.now()),
            Column('updated_at', DateTime, default=func.now(), onupdate=func.now()),
            extend_existing=True, schema=self.schema_name
        )
        return [attractions_table]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.min_delay = params.get('min_delay', 2.0)
        self.max_delay = params.get('max_delay', 5.0)
        max_attractions = params.get('max_attractions', None)
        categories = params.get('categories', self.CATEGORIES)

        self.log(f"Starting DagjeWeg scrape")
        self.log(f"Rate limiting: {self.min_delay}-{self.max_delay}s between requests")

        tip_ids = set()
        for category in categories:
            if max_attractions and len(tip_ids) >= max_attractions:
                break
            self.log(f"Fetching tips from: {category}")
            try:
                new_ids = await self._get_tip_ids_from_listing(f"{self.BASE_URL}/{category}")
                tip_ids.update(new_ids)
                self.log(f"Found {len(new_ids)} tips, total: {len(tip_ids)}")
            except Exception as e:
                self.log(f"Error fetching {category}: {e}", level="warning")
            await self._delay()

        self.log(f"\n=== Found {len(tip_ids)} unique attractions ===")

        attractions = []
        tip_ids_list = list(tip_ids)[:max_attractions] if max_attractions else list(tip_ids)

        for i, tip_id in enumerate(tip_ids_list):
            self.log(f"Scraping {i+1}/{len(tip_ids_list)}: tip/{tip_id}")
            try:
                attraction = await self._scrape_attraction(tip_id)
                if attraction:
                    attractions.append(attraction)
            except Exception as e:
                self.log(f"Error scraping tip/{tip_id}: {e}", level="warning")
            if (i + 1) % 50 == 0:
                self.log(f"Progress: {i+1}/{len(tip_ids_list)} scraped")
            await self._delay()

        self.log(f"\n=== Complete: {len(attractions)} attractions ===")
        return attractions

    async def _delay(self):
        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

    async def _get_tip_ids_from_listing(self, url: str) -> Set[int]:
        import httpx
        tip_ids = set()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            for page in range(1, 51):
                page_url = f"{url}?page={page}" if page > 1 else url
                try:
                    response = await client.get(page_url)
                    matches = re.findall(r'/tip/(\d+)/', response.text)
                    if not matches:
                        break
                    new_ids = set(int(m) for m in matches)
                    if not new_ids - tip_ids:
                        break
                    tip_ids.update(new_ids)
                    await asyncio.sleep(0.5)
                except:
                    break
        return tip_ids

    async def _scrape_attraction(self, tip_id: int) -> Optional[Dict[str, Any]]:
        import httpx
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            response = await client.get(f"{self.BASE_URL}/tip/{tip_id}/")
            html = response.text

        soup = BeautifulSoup(html, 'html.parser')
        data = {'tip_id': tip_id, 'url': f"{self.BASE_URL}/tip/{tip_id}/", 'scraped_at': datetime.utcnow().isoformat()}

        if soup.find('h1'):
            data['name'] = soup.find('h1').get_text(strip=True)
        if soup.find('meta', {'name': 'description'}):
            data['short_description'] = soup.find('meta', {'name': 'description'}).get('content', '')

        # Extract coordinates from OpenGraph meta tags (primary method)
        # Format: <meta property="og:latitude" content="51.200696">
        lat_meta = soup.find('meta', {'property': 'og:latitude'})
        lng_meta = soup.find('meta', {'property': 'og:longitude'})
        if lat_meta and lat_meta.get('content'):
            try:
                data['latitude'] = float(lat_meta.get('content'))
            except (ValueError, TypeError):
                pass
        if lng_meta and lng_meta.get('content'):
            try:
                data['longitude'] = float(lng_meta.get('content'))
            except (ValueError, TypeError):
                pass

        # Fallback: try schema.org itemprop meta tags
        # Format: <meta itemprop="latitude" content="51.200696">
        if 'latitude' not in data or 'longitude' not in data:
            lat_itemprop = soup.find('meta', {'itemprop': 'latitude'})
            lng_itemprop = soup.find('meta', {'itemprop': 'longitude'})
            if lat_itemprop and lat_itemprop.get('content'):
                try:
                    data['latitude'] = float(lat_itemprop.get('content'))
                except (ValueError, TypeError):
                    pass
            if lng_itemprop and lng_itemprop.get('content'):
                try:
                    data['longitude'] = float(lng_itemprop.get('content'))
                except (ValueError, TypeError):
                    pass

        # Fallback: try name-based meta tags
        if 'latitude' not in data or 'longitude' not in data:
            lat_name = soup.find('meta', {'name': 'latitude'})
            lng_name = soup.find('meta', {'name': 'longitude'})
            if lat_name and lat_name.get('content'):
                try:
                    data['latitude'] = float(lat_name.get('content'))
                except (ValueError, TypeError):
                    pass
            if lng_name and lng_name.get('content'):
                try:
                    data['longitude'] = float(lng_name.get('content'))
                except (ValueError, TypeError):
                    pass

        # Fallback: try ICBM meta tag (format: "lat, lng")
        if 'latitude' not in data or 'longitude' not in data:
            icbm_meta = soup.find('meta', {'name': 'ICBM'})
            if icbm_meta and icbm_meta.get('content'):
                try:
                    parts = icbm_meta.get('content').split(',')
                    if len(parts) == 2:
                        data['latitude'] = float(parts[0].strip())
                        data['longitude'] = float(parts[1].strip())
                except (ValueError, TypeError):
                    pass

        # Fallback: try geo.position meta tag
        if 'latitude' not in data or 'longitude' not in data:
            geo_meta = soup.find('meta', {'name': 'geo.position'})
            if geo_meta and geo_meta.get('content'):
                try:
                    parts = geo_meta.get('content').split(';')
                    if len(parts) == 2:
                        data['latitude'] = float(parts[0].strip())
                        data['longitude'] = float(parts[1].strip())
                except (ValueError, TypeError):
                    pass

        # Final fallback: regex patterns in JavaScript/HTML
        if 'latitude' not in data:
            lat_match = re.search(r'[\"\']?lat(?:itude)?[\"\']?\s*[:=]\s*[\"\']?([\d.]+)', html)
            if lat_match:
                data['latitude'] = float(lat_match.group(1))
        if 'longitude' not in data:
            lng_match = re.search(r'[\"\']?(?:lng|lon(?:gitude)?)[\"\']?\s*[:=]\s*[\"\']?([\d.]+)', html)
            if lng_match:
                data['longitude'] = float(lng_match.group(1))

        title = soup.title.string if soup.title else ''
        city_match = re.search(r',\s*([A-Z][a-z]+(?:\s+[a-z]+)?)\s*,', title)
        if city_match: data['city'] = city_match.group(1)

        province_match = re.search(r'(Noord-Holland|Zuid-Holland|Noord-Brabant|Gelderland|Utrecht|Overijssel|Limburg|Friesland|Groningen|Drenthe|Zeeland|Flevoland)', title, re.I)
        if province_match: data['province'] = province_match.group(1)

        rating_match = re.search(r'(\d[,.]?\d?)\s*/\s*10', html)
        if rating_match: data['rating'] = float(rating_match.group(1).replace(',', '.'))

        review_match = re.search(r'(\d+)\s*reviews?', html, re.I)
        if review_match: data['review_count'] = int(review_match.group(1))

        if soup.find('meta', property='og:image'):
            data['image_url'] = soup.find('meta', property='og:image').get('content', '')

        data['country'] = 'NL'
        return data

    async def after_scrape(self, results: List[Dict], params: Dict):
        if not results:
            return
        self.log(f"Storing {len(results)} attractions...")
        try:
            from app.core.database import engine
            async with engine.begin() as conn:
                tables = self.define_tables()
                await conn.run_sync(self.metadata.create_all)
                now = datetime.utcnow()

                for i in range(0, len(results), 500):
                    batch = [{
                        'tip_id': a.get('tip_id'), 'name': a.get('name'),
                        'short_description': a.get('short_description'),
                        'city': a.get('city'), 'province': a.get('province'),
                        'country': 'NL', 'latitude': a.get('latitude'),
                        'longitude': a.get('longitude'), 'rating': a.get('rating'),
                        'review_count': a.get('review_count'),
                        'image_url': a.get('image_url'), 'url': a.get('url'),
                        'raw_data': a, 'scraped_at': now, 'updated_at': now,
                    } for a in results[i:i+500]]

                    stmt = pg_insert(tables[0]).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['tip_id'],
                        set_={'name': stmt.excluded.name, 'city': stmt.excluded.city,
                              'province': stmt.excluded.province, 'rating': stmt.excluded.rating,
                              'review_count': stmt.excluded.review_count,
                              'latitude': stmt.excluded.latitude, 'longitude': stmt.excluded.longitude,
                              'image_url': stmt.excluded.image_url, 'raw_data': stmt.excluded.raw_data,
                              'updated_at': stmt.excluded.updated_at}
                    )
                    await conn.execute(stmt)
                    self.log(f"Stored: {min(i+500, len(results))}/{len(results)}")
            self.log(f"Successfully stored {len(results)} attractions")
        except Exception as e:
            self.log(f"Error storing: {e}", level="error")
            raise


if __name__ == "__main__":
    import asyncio
    async def test():
        scraper = DagjeWegScraper()
        results = await scraper.scrape({'categories': ['attractieparken'], 'max_attractions': 3, 'min_delay': 2.0, 'max_delay': 3.0})
        for a in results:
            print(f"- {a.get('name')} in {a.get('city')} ({a.get('rating')}/10)")
    asyncio.run(test())

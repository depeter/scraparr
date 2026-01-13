#!/usr/bin/env python3
"""
Ticketmaster Event Scraper for Scraparr
API-based scraper using Ticketmaster Discovery API
https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
"""

import asyncio
import httpx
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Float, Boolean
import logging
import os

# Import the base scraper from the Scraparr framework
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from app.scrapers.base import BaseScraper, ScraperType
except ImportError:
    # Fallback for when running standalone
    class BaseScraper:
        pass
    class ScraperType:
        API = "api"

logger = logging.getLogger(__name__)


# European countries with Ticketmaster presence
EUROPEAN_COUNTRIES = {
    "austria": {"name": "Austria", "code": "AT"},
    "belgium": {"name": "Belgium", "code": "BE"},
    "bulgaria": {"name": "Bulgaria", "code": "BG"},
    "croatia": {"name": "Croatia", "code": "HR"},
    "czech-republic": {"name": "Czech Republic", "code": "CZ"},
    "denmark": {"name": "Denmark", "code": "DK"},
    "finland": {"name": "Finland", "code": "FI"},
    "france": {"name": "France", "code": "FR"},
    "germany": {"name": "Germany", "code": "DE"},
    "greece": {"name": "Greece", "code": "GR"},
    "hungary": {"name": "Hungary", "code": "HU"},
    "iceland": {"name": "Iceland", "code": "IS"},
    "ireland": {"name": "Ireland", "code": "IE"},
    "italy": {"name": "Italy", "code": "IT"},
    "netherlands": {"name": "Netherlands", "code": "NL"},
    "norway": {"name": "Norway", "code": "NO"},
    "poland": {"name": "Poland", "code": "PL"},
    "portugal": {"name": "Portugal", "code": "PT"},
    "romania": {"name": "Romania", "code": "RO"},
    "spain": {"name": "Spain", "code": "ES"},
    "sweden": {"name": "Sweden", "code": "SE"},
    "switzerland": {"name": "Switzerland", "code": "CH"},
    "turkey": {"name": "Turkey", "code": "TR"},
    "united-kingdom": {"name": "United Kingdom", "code": "GB"},
}


class TicketmasterScraper(BaseScraper):
    """Scraper for Ticketmaster events using Discovery API v2"""

    scraper_type = ScraperType.API

    BASE_URL = "https://app.ticketmaster.com/discovery/v2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default rate limiting - Ticketmaster has rate limits, be respectful
        self.min_delay = 0.5
        self.max_delay = 2.0

    def define_tables(self) -> List[Table]:
        """Define database tables for Ticketmaster events"""
        events_table = Table(
            'events',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('event_id', String(100), unique=True, nullable=False),  # Ticketmaster event ID
            Column('name', String(500), nullable=False),
            Column('description', Text),
            Column('url', String(1000), nullable=False),
            Column('info', Text),  # Additional info/pleaseNote field
            Column('start_date', DateTime),
            Column('start_date_local', String(100)),  # Local date/time as string
            Column('timezone', String(100)),
            Column('status_code', String(50)),  # onsale, offsale, cancelled, etc.
            Column('venue_id', String(100)),
            Column('venue_name', String(500)),
            Column('venue_address', String(500)),
            Column('city', String(255)),
            Column('postal_code', String(20)),
            Column('country', String(100)),
            Column('country_code', String(5)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('price_min', Float),
            Column('price_max', Float),
            Column('currency', String(10)),
            Column('genre', String(255)),  # Primary genre
            Column('segment', String(100)),  # Music, Sports, Arts, etc.
            Column('classifications', Text),  # JSON string of all classifications
            Column('promoter_id', String(100)),
            Column('promoter_name', String(500)),
            Column('image_url', String(1000)),
            Column('image_ratio', String(20)),  # 16_9, 3_2, 4_3, etc.
            Column('external_links', Text),  # JSON of social media links
            Column('scraped_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            extend_existing=True,
            schema=self.schema_name
        )
        return [events_table]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape events from Ticketmaster Discovery API

        Params:
            api_key: Ticketmaster API key (required) - Get from https://developer.ticketmaster.com/
            country_code: Country code (e.g., "GB", "DE", "FR") or country slug (e.g., "united-kingdom")
                          Use "all" to scrape all European countries
            city: Optional city name to filter (e.g., "London", "Berlin")
            keyword: Optional search keyword (e.g., "rock", "jazz", "football")
            genre_id: Optional genre ID from Ticketmaster API
            segment_name: Optional segment (Music, Sports, Arts & Theatre, Film, Miscellaneous)
            start_date: Optional start date in format YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ
            end_date: Optional end date in format YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ
            size: Events per page (default: 200, max: 200)
            max_events: Maximum total events to scrape (default: 5000)
            min_delay: Minimum delay between requests in seconds (default: 0.5)
            max_delay: Maximum delay between requests in seconds (default: 2.0)

        Returns:
            List of event dictionaries
        """
        api_key = params.get('api_key')
        if not api_key:
            raise ValueError("api_key is required. Get one from https://developer.ticketmaster.com/")

        country = params.get('country_code', params.get('country', 'GB'))
        city = params.get('city')
        keyword = params.get('keyword')
        genre_id = params.get('genre_id')
        segment_name = params.get('segment_name')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        size = min(params.get('size', 200), 200)  # API max is 200
        max_events = params.get('max_events', 5000)
        min_delay = params.get('min_delay', self.min_delay)
        max_delay = params.get('max_delay', self.max_delay)

        self.log(f"Starting Ticketmaster scrape with params: {params}")
        self.log(f"Rate limiting: random delay between {min_delay}s and {max_delay}s per request")

        # Determine which countries to scrape
        countries_to_scrape = []
        if country.lower() == "all":
            countries_to_scrape = [info['code'] for info in EUROPEAN_COUNTRIES.values()]
            self.log(f"Scraping all {len(countries_to_scrape)} European countries")
        elif len(country) == 2:
            # Already a country code
            countries_to_scrape = [country.upper()]
        elif country.lower() in EUROPEAN_COUNTRIES:
            # Country slug provided
            countries_to_scrape = [EUROPEAN_COUNTRIES[country.lower()]['code']]
        else:
            self.log(f"Unknown country: {country}. Available: {', '.join(EUROPEAN_COUNTRIES.keys())}", level="error")
            raise ValueError(f"Unknown country: {country}")

        all_events = []
        seen_event_ids = set()

        for country_code in countries_to_scrape:
            country_name = next((c['name'] for c in EUROPEAN_COUNTRIES.values() if c['code'] == country_code), country_code)
            self.log(f"Scraping {country_name} ({country_code})...")

            try:
                events = await self._scrape_country(
                    api_key=api_key,
                    country_code=country_code,
                    city=city,
                    keyword=keyword,
                    genre_id=genre_id,
                    segment_name=segment_name,
                    start_date=start_date,
                    end_date=end_date,
                    size=size,
                    max_events=max_events,
                    min_delay=min_delay,
                    max_delay=max_delay,
                    seen_event_ids=seen_event_ids
                )
                all_events.extend(events)
                self.log(f"Scraped {len(events)} events from {country_name}")
            except Exception as e:
                self.log(f"Error scraping {country_name}: {str(e)}", level="error")
                continue

        self.log(f"Scraping complete. Total unique events: {len(all_events)}")
        return all_events

    async def _scrape_country(
        self,
        api_key: str,
        country_code: str,
        city: Optional[str],
        keyword: Optional[str],
        genre_id: Optional[str],
        segment_name: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        size: int,
        max_events: int,
        min_delay: float,
        max_delay: float,
        seen_event_ids: set
    ) -> List[Dict[str, Any]]:
        """Scrape events from a specific country"""

        events = []
        page = 0
        total_pages = None

        while len(events) < max_events:
            # Build query parameters
            query_params = {
                'apikey': api_key,
                'countryCode': country_code,
                'size': size,
                'page': page,
                'sort': 'date,asc',  # Sort by date ascending
            }

            if city:
                query_params['city'] = city
            if keyword:
                query_params['keyword'] = keyword
            if genre_id:
                query_params['genreId'] = genre_id
            if segment_name:
                query_params['segmentName'] = segment_name
            if start_date:
                query_params['startDateTime'] = start_date
            if end_date:
                query_params['endDateTime'] = end_date

            # Rate limiting
            delay = random.uniform(min_delay, max_delay)
            self.log(f"Page {page}: Waiting {delay:.2f}s before request...")
            await asyncio.sleep(delay)

            try:
                # Make API request
                url = f"{self.BASE_URL}/events.json"
                response = await self.http_client.get(url, params=query_params)
                response.raise_for_status()

                data = response.json()

                # Check if there are events
                embedded = data.get('_embedded', {})
                page_events = embedded.get('events', [])

                if not page_events:
                    self.log(f"No more events found for {country_code} (page {page})")
                    break

                # Extract pagination info
                page_data = data.get('page', {})
                total_pages = page_data.get('totalPages', 1)
                total_elements = page_data.get('totalElements', 0)

                self.log(f"Page {page + 1}/{total_pages}: Found {len(page_events)} events (total available: {total_elements})")

                # Process events
                for event_data in page_events:
                    try:
                        parsed_event = self._parse_event(event_data, country_code)
                        if parsed_event and parsed_event['event_id'] not in seen_event_ids:
                            events.append(parsed_event)
                            seen_event_ids.add(parsed_event['event_id'])
                    except Exception as e:
                        self.log(f"Error parsing event: {str(e)}", level="warning")
                        continue

                # Check if we've reached the last page
                page += 1

                # Check API pagination limit: (page * size) must be < 1000
                if (page * size) >= 1000:
                    self.log(f"Reached Ticketmaster API pagination limit (page * size >= 1000). Scraped {len(events)} events.", level="warning")
                    break

                if page >= total_pages:
                    self.log(f"Reached last page ({total_pages}) for {country_code}")
                    break

                # Check if we've reached max events
                if len(events) >= max_events:
                    self.log(f"Reached max events limit ({max_events}) for {country_code}")
                    break

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    self.log(f"Rate limited by API, waiting 60 seconds...", level="warning")
                    await asyncio.sleep(60)
                    continue
                else:
                    self.log(f"HTTP error: {e.response.status_code} - {e.response.text}", level="error")
                    break
            except Exception as e:
                self.log(f"Error fetching page {page}: {str(e)}", level="error")
                break

        return events

    def _parse_event(self, event_data: Dict, country_code: str) -> Optional[Dict[str, Any]]:
        """Parse an event from API response"""

        try:
            # Basic event info
            event_id = event_data.get('id')
            if not event_id:
                return None

            name = event_data.get('name', 'Unknown Event')
            url = event_data.get('url', '')
            info = event_data.get('info', '')
            please_note = event_data.get('pleaseNote', '')
            if please_note:
                info = f"{info}\n\n{please_note}" if info else please_note

            # Dates
            dates = event_data.get('dates', {})
            start = dates.get('start', {})
            start_date = None
            start_date_local = start.get('dateTime') or start.get('localDate')
            timezone_str = dates.get('timezone', '')

            if start_date_local:
                try:
                    # Try to parse as datetime
                    if 'T' in start_date_local:
                        start_date = datetime.fromisoformat(start_date_local.replace('Z', '+00:00'))
                        # Remove timezone info for database compatibility (TIMESTAMP WITHOUT TIME ZONE)
                        start_date = start_date.replace(tzinfo=None)
                    else:
                        start_date = datetime.strptime(start_date_local, '%Y-%m-%d')
                except:
                    pass

            status_code = dates.get('status', {}).get('code', '')

            # Venue information
            embedded = event_data.get('_embedded', {})
            venues = embedded.get('venues', [])
            venue_id = None
            venue_name = None
            venue_address = None
            city = None
            postal_code = None
            country = None
            latitude = None
            longitude = None

            if venues:
                venue = venues[0]
                venue_id = venue.get('id')
                venue_name = venue.get('name')

                address = venue.get('address', {})
                venue_address = address.get('line1', '')

                city_data = venue.get('city', {})
                if isinstance(city_data, dict):
                    city = city_data.get('name')
                elif isinstance(city_data, str):
                    city = city_data

                postal_code = venue.get('postalCode')

                country_data = venue.get('country', {})
                if isinstance(country_data, dict):
                    country = country_data.get('name')
                elif isinstance(country_data, str):
                    country = country_data

                location = venue.get('location', {})
                if location:
                    try:
                        latitude = float(location.get('latitude'))
                        longitude = float(location.get('longitude'))
                    except (TypeError, ValueError):
                        pass

            # Price information
            price_ranges = event_data.get('priceRanges', [])
            price_min = None
            price_max = None
            currency = None

            if price_ranges:
                price_range = price_ranges[0]
                try:
                    price_min = float(price_range.get('min', 0))
                    price_max = float(price_range.get('max', 0))
                except (TypeError, ValueError):
                    pass
                currency = price_range.get('currency')

            # Classifications (genre, segment)
            classifications = event_data.get('classifications', [])
            genre = None
            segment = None
            classifications_json = None

            if classifications:
                classification = classifications[0]

                genre_data = classification.get('genre', {})
                if isinstance(genre_data, dict):
                    genre = genre_data.get('name')

                segment_data = classification.get('segment', {})
                if isinstance(segment_data, dict):
                    segment = segment_data.get('name')

                # Store full classifications as string
                import json
                classifications_json = json.dumps(classifications)

            # Promoter information
            promoters = embedded.get('promoters', [])
            promoter_id = None
            promoter_name = None

            if promoters:
                promoter = promoters[0]
                promoter_id = promoter.get('id')
                promoter_name = promoter.get('name')

            # Images
            images = event_data.get('images', [])
            image_url = None
            image_ratio = None

            if images:
                # Find best quality image (prefer 16_9 ratio)
                best_image = None
                for img in images:
                    if img.get('ratio') == '16_9':
                        best_image = img
                        break
                if not best_image:
                    best_image = images[0]

                image_url = best_image.get('url')
                image_ratio = best_image.get('ratio')

            # External links (social media, etc.)
            external_links = event_data.get('externalLinks', {})
            import json
            external_links_json = json.dumps(external_links) if external_links else None

            return {
                'event_id': event_id,
                'name': name,
                'description': None,  # Ticketmaster doesn't provide descriptions in list view
                'url': url,
                'info': info,
                'start_date': start_date,
                'start_date_local': start_date_local,
                'timezone': timezone_str,
                'status_code': status_code,
                'venue_id': venue_id,
                'venue_name': venue_name,
                'venue_address': venue_address,
                'city': city,
                'postal_code': postal_code,
                'country': country,
                'country_code': country_code,
                'latitude': latitude,
                'longitude': longitude,
                'price_min': price_min,
                'price_max': price_max,
                'currency': currency,
                'genre': genre,
                'segment': segment,
                'classifications': classifications_json,
                'promoter_id': promoter_id,
                'promoter_name': promoter_name,
                'image_url': image_url,
                'image_ratio': image_ratio,
                'external_links': external_links_json,
                'scraped_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

        except Exception as e:
            self.log(f"Error parsing event {event_data.get('id')}: {str(e)}", level="error")
            return None

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Save scraped events to database"""
        if not results:
            self.log("No events to save")
            return

        self.log(f"Saving {len(results)} events to database...")

        # Get database engine
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        # Import database URL from environment or use default
        database_url = os.getenv(
            'DATABASE_URL',
            'postgresql+asyncpg://scraparr:scraparr@postgres:5432/scraparr'
        )
        engine = create_async_engine(database_url)

        # Define tables
        tables = self.define_tables()
        events_table = tables[0]

        try:
            async with engine.begin() as conn:
                # Create schema if it doesn't exist
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))

                # Create tables
                await conn.run_sync(self.metadata.create_all)

                # Insert or update events (upsert on event_id)
                for event in results:
                    # Check if event already exists
                    check_query = events_table.select().where(
                        events_table.c.event_id == event['event_id']
                    )
                    result = await conn.execute(check_query)
                    existing = result.fetchone()

                    if existing:
                        # Update existing event
                        update_query = events_table.update().where(
                            events_table.c.event_id == event['event_id']
                        ).values(**event)
                        await conn.execute(update_query)
                    else:
                        # Insert new event
                        insert_query = events_table.insert().values(**event)
                        await conn.execute(insert_query)

            self.log(f"Successfully saved {len(results)} events to database")

        except Exception as e:
            self.log(f"Error saving to database: {str(e)}", level="error")
            raise
        finally:
            await engine.dispose()


# Main function for testing
async def main():
    """Test the scraper"""
    scraper = TicketmasterScraper(
        scraper_id=999,
        schema_name="scraper_test",
        config={}
    )

    try:
        # You need a Ticketmaster API key from https://developer.ticketmaster.com/
        api_key = os.getenv('TICKETMASTER_API_KEY', 'YOUR_API_KEY_HERE')

        params = {
            'api_key': api_key,
            'country_code': 'GB',  # United Kingdom
            'size': 50,
            'max_events': 100,
            'min_delay': 1.0,
            'max_delay': 2.0
        }

        results = await scraper.scrape(params)
        print(f"\n{'='*80}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*80}")
        print(f"Total events found: {len(results)}")
        print(f"\nFirst 5 events:")
        for i, event in enumerate(results[:5], 1):
            print(f"\n{i}. {event['name']}")
            print(f"   ID: {event['event_id']}")
            print(f"   Date: {event.get('start_date_local', 'N/A')}")
            print(f"   Venue: {event.get('venue_name', 'N/A')}")
            print(f"   City: {event.get('city', 'N/A')}")
            print(f"   Genre: {event.get('genre', 'N/A')}")
            print(f"   URL: {event['url']}")

        print(f"\n{'='*80}")
        print("LOGS:")
        print(f"{'='*80}")
        print(scraper.get_logs())

    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

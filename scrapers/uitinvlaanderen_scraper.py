#!/usr/bin/env python3
"""
UiTinVlaanderen Event Scraper for Scraparr
GraphQL-based scraper for UiT in Vlaanderen events (uses api.uit.be)
"""

import asyncio
import httpx
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Float

# Import the base scraper from the Scraparr framework
import sys
import os
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


class UiTinVlaanderenScraper(BaseScraper):
    """Scraper for UiTinVlaanderen events via GraphQL API"""

    scraper_type = ScraperType.API

    GRAPHQL_URL = "https://api.uit.be/graphql"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default rate limiting - will be overridden by params if provided
        self.min_delay = 1.0
        self.max_delay = 3.0

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape events from UiT in Vlaanderen GraphQL API

        Params:
            query: Optional free text search
            region: Region filter (e.g., "Antwerpen", "Gent", "Leuven")
            postal_codes: List of postal codes to filter by
            event_types: List of event types (e.g., ["Concert", "Festival"])
            max_results: Maximum number of events to scrape (default: 100)
            limit_per_page: Items per API request (default: 50, max: 100)
            min_delay: Minimum delay between requests in seconds (default: 1.0)
            max_delay: Maximum delay between requests in seconds (default: 3.0)

        Returns:
            List of event dictionaries
        """
        max_results = params.get('max_results', 100)
        limit_per_page = min(params.get('limit_per_page', 50), 100)  # GraphQL typically has limits

        # Get rate limiting params
        min_delay = params.get('min_delay', self.min_delay)
        max_delay = params.get('max_delay', self.max_delay)

        # API has a hard limit: start + limit must be <= 10000
        # So we can't fetch more than 10000 events total
        if max_results > 10000:
            self.log(f"max_results ({max_results}) exceeds API limit of 10000, capping at 10000", level="warning")
            max_results = 10000

        events = []
        offset = 0

        self.log(f"Starting UiTinVlaanderen GraphQL scrape with params: {params}")
        self.log(f"Rate limiting: random delay between {min_delay}s and {max_delay}s per request")

        # Build GraphQL query variables
        variables = self._build_variables(params, limit_per_page, offset)

        headers = {
            'Content-Type': 'application/json',
            'apollo-require-preflight': 'true',  # Required for CSRF protection
            'User-Agent': 'Scraparr-UiTinVlaanderen/2.0'
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            while len(events) < max_results:
                # Check if we're approaching the API pagination limit
                if offset + limit_per_page > 10000:
                    self.log(f"Approaching API pagination limit (offset={offset}), stopping scrape", level="warning")
                    break

                # Update offset for pagination
                variables['offset'] = offset
                variables['limit'] = min(limit_per_page, max_results - len(events))

                # GraphQL query
                graphql_query = self._build_graphql_query()

                payload = {
                    "query": graphql_query,
                    "variables": variables
                }

                self.log(f"Fetching page {offset // limit_per_page + 1}, offset: {offset}, limit: {variables['limit']}")

                try:
                    # Random rate limiting to be respectful and avoid detection
                    delay = random.uniform(min_delay, max_delay)
                    self.log(f"Waiting {delay:.2f} seconds before next request...")
                    await asyncio.sleep(delay)

                    response = await client.post(self.GRAPHQL_URL, json=payload)

                    # Log response for debugging
                    if response.status_code != 200:
                        logger.error(f"HTTP {response.status_code}: {response.text}")

                    response.raise_for_status()
                    data = response.json()

                    # Check for GraphQL errors
                    if 'errors' in data:
                        self.log(f"GraphQL errors: {data['errors']}", level="error")
                        break

                    # Parse events from response
                    if 'data' not in data or 'events' not in data['data']:
                        self.log("No events data in response", level="warning")
                        break

                    events_data = data['data']['events']
                    total_items = events_data.get('totalItems', 0)

                    self.log(f"Total events available: {total_items}")

                    event_list = events_data.get('data', [])

                    if not event_list:
                        self.log("No more events to fetch")
                        break

                    for event_data in event_list:
                        if len(events) >= max_results:
                            break

                        event = self._parse_event(event_data)
                        if event:
                            events.append(event)

                    # Check if we've fetched all available events
                    if offset + len(event_list) >= total_items:
                        self.log("Reached end of available events")
                        break

                    offset += len(event_list)

                except httpx.HTTPError as e:
                    self.log(f"HTTP error: {e}", level="error")
                    break
                except Exception as e:
                    self.log(f"Error during scrape: {e}", level="error")
                    break

        self.log(f"Scraped {len(events)} events from UiTinVlaanderen")
        return events

    def _build_graphql_query(self) -> str:
        """Build the GraphQL query string"""
        return """
        query GetEvents($limit: Float, $offset: Float) {
          events(
            limit: $limit
            offset: $offset
          ) {
            totalItems
            data {
              ... on Event {
                id
                name
                description
                location {
                  name
                  address {
                    streetAddress
                    locality
                    postalCode
                  }
                  geo {
                    lat
                    lng
                  }
                }
                images {
                  url
                }
                calendar {
                  startDate
                  endDate
                }
                types {
                  name
                }
                themes {
                  name
                }
                organizer {
                  name
                }
              }
            }
          }
        }
        """

    def _build_variables(self, params: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        """Build GraphQL query variables from params"""
        variables = {
            "limit": limit,
            "offset": offset
        }

        # Text search
        if params.get('query'):
            variables['textQuery'] = params['query']

        # Region filter (would need region IDs - for now we'll use postal codes)
        if params.get('region'):
            # This is a simplified approach - ideally we'd map region names to IDs
            pass  # Region filtering not implemented yet

        # Postal codes filter
        if params.get('postal_codes'):
            variables['postalCodes'] = params['postal_codes']

        # Event type filter (would need type IDs)
        if params.get('event_types'):
            # Similar to regions, we'd need to map type names to IDs
            pass  # Event type filtering not implemented yet

        return variables

    def _parse_event(self, event_data: Dict) -> Optional[Dict[str, Any]]:
        """Parse event data into standardized format"""
        try:
            # Event ID
            event_id = event_data.get('id')
            if not event_id:
                return None

            # Basic info
            name = event_data.get('name', 'Unknown')
            description = event_data.get('description', '')

            # Location
            location = event_data.get('location', {})
            location_name = location.get('name', '')

            address = location.get('address', {})
            street_address = address.get('streetAddress', '')
            city = address.get('locality', '')
            postal_code = address.get('postalCode', '')

            # Coordinates
            geo = location.get('geo')
            latitude = geo.get('lat') if geo else None
            longitude = geo.get('lng') if geo else None

            # Calendar
            calendar = event_data.get('calendar', {})
            start_date = calendar.get('startDate')
            end_date = calendar.get('endDate')

            # Images
            images = event_data.get('images', [])
            image_url = images[0].get('url') if images else None

            # Types and themes
            types = event_data.get('types', [])
            event_type = types[0].get('name') if types else None

            themes = event_data.get('themes', [])
            theme_names = [t.get('name') for t in themes if t.get('name')]
            themes_str = ', '.join(theme_names) if theme_names else None

            # Organizer
            organizer = event_data.get('organizer', {})
            organizer_name = organizer.get('name') if organizer else None

            # Build URL
            url = f"https://www.uitinvlaanderen.be/agenda/e/{event_id}"

            return {
                'event_id': event_id,
                'name': name,
                'description': description,
                'start_date': start_date,
                'end_date': end_date,
                'location_name': location_name,
                'street_address': street_address,
                'city': city,
                'postal_code': postal_code,
                'country': 'BE',  # Always Belgium
                'latitude': latitude,
                'longitude': longitude,
                'organizer': organizer_name,
                'event_type': event_type,
                'themes': themes_str,
                'url': url,
                'image_url': image_url,
                'scraped_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error parsing event: {e}", exc_info=True)
            return None

    def define_tables(self):
        """Define database tables for UiTinVlaanderen events"""
        events_table = Table(
            'events',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('event_id', String(100), unique=True, nullable=False, index=True),
            Column('name', String(500)),
            Column('description', Text),
            Column('start_date', String(100)),
            Column('end_date', String(100)),
            Column('location_name', String(300)),
            Column('street_address', String(300)),
            Column('city', String(100), index=True),
            Column('postal_code', String(20)),
            Column('country', String(100)),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('organizer', String(300)),
            Column('event_type', String(100), index=True),
            Column('themes', String(500)),
            Column('url', String(500)),
            Column('image_url', String(500)),
            Column('scraped_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            extend_existing=True,
            schema=self.schema_name
        )

        return [events_table]

    async def after_scrape(self, results: List[Dict], params: Dict):
        """Store scraped events in database"""
        if not results:
            self.log("No events found")
            return

        self.log(f"Storing {len(results)} events in database...")

        try:
            from app.core.database import engine
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            async with engine.begin() as conn:
                # Get table reference
                tables = self.define_tables()
                events_table = tables[0]

                # Create table if it doesn't exist
                await conn.run_sync(self.metadata.create_all)

                # Insert or update events
                for event in results:
                    event_data = {
                        'event_id': event.get('event_id'),
                        'name': event.get('name'),
                        'description': event.get('description'),
                        'start_date': event.get('start_date'),
                        'end_date': event.get('end_date'),
                        'location_name': event.get('location_name'),
                        'street_address': event.get('street_address'),
                        'city': event.get('city'),
                        'postal_code': event.get('postal_code'),
                        'country': event.get('country', 'BE'),
                        'latitude': event.get('latitude'),
                        'longitude': event.get('longitude'),
                        'organizer': event.get('organizer'),
                        'event_type': event.get('event_type'),
                        'themes': event.get('themes'),
                        'url': event.get('url'),
                        'image_url': event.get('image_url'),
                        'scraped_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                    }

                    # Upsert event (insert or update if exists)
                    stmt = pg_insert(events_table).values(**event_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['event_id'],
                        set_={
                            'name': stmt.excluded.name,
                            'description': stmt.excluded.description,
                            'start_date': stmt.excluded.start_date,
                            'end_date': stmt.excluded.end_date,
                            'location_name': stmt.excluded.location_name,
                            'street_address': stmt.excluded.street_address,
                            'city': stmt.excluded.city,
                            'postal_code': stmt.excluded.postal_code,
                            'country': stmt.excluded.country,
                            'latitude': stmt.excluded.latitude,
                            'longitude': stmt.excluded.longitude,
                            'organizer': stmt.excluded.organizer,
                            'event_type': stmt.excluded.event_type,
                            'themes': stmt.excluded.themes,
                            'url': stmt.excluded.url,
                            'image_url': stmt.excluded.image_url,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )

                    await conn.execute(stmt)

            self.log(f"Successfully stored {len(results)} events in database")

        except Exception as e:
            self.log(f"Error storing events in database: {str(e)}", level="error")
            raise


# For standalone testing
if __name__ == "__main__":
    import asyncio

    async def test():
        scraper = UiTinVlaanderenScraper()
        params = {
            'max_results': 10
        }
        results = await scraper.scrape(params)
        print(f"Found {len(results)} events")
        for event in results[:3]:
            print(f"- {event['name']} in {event['city']}")

    asyncio.run(test())

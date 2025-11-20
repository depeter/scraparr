#!/usr/bin/env python3
"""
Eventbrite Event Scraper for Scraparr
Web scraper for Eventbrite events across European countries
"""

import asyncio
import httpx
import random
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Float, Boolean
import logging

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
        WEB = "web"

logger = logging.getLogger(__name__)


# European countries with Eventbrite presence
EUROPEAN_COUNTRIES = {
    "austria": {"name": "Austria", "code": "AT"},
    "belgium": {"name": "Belgium", "code": "BE"},
    "bulgaria": {"name": "Bulgaria", "code": "BG"},
    "croatia": {"name": "Croatia", "code": "HR"},
    "czech-republic": {"name": "Czech Republic", "code": "CZ"},
    "denmark": {"name": "Denmark", "code": "DK"},
    "estonia": {"name": "Estonia", "code": "EE"},
    "finland": {"name": "Finland", "code": "FI"},
    "france": {"name": "France", "code": "FR"},
    "germany": {"name": "Germany", "code": "DE"},
    "greece": {"name": "Greece", "code": "GR"},
    "hungary": {"name": "Hungary", "code": "HU"},
    "iceland": {"name": "Iceland", "code": "IS"},
    "ireland": {"name": "Ireland", "code": "IE"},
    "italy": {"name": "Italy", "code": "IT"},
    "latvia": {"name": "Latvia", "code": "LV"},
    "lithuania": {"name": "Lithuania", "code": "LT"},
    "netherlands": {"name": "Netherlands", "code": "NL"},
    "norway": {"name": "Norway", "code": "NO"},
    "poland": {"name": "Poland", "code": "PL"},
    "portugal": {"name": "Portugal", "code": "PT"},
    "romania": {"name": "Romania", "code": "RO"},
    "serbia": {"name": "Serbia", "code": "RS"},
    "slovakia": {"name": "Slovakia", "code": "SK"},
    "slovenia": {"name": "Slovenia", "code": "SI"},
    "spain": {"name": "Spain", "code": "ES"},
    "sweden": {"name": "Sweden", "code": "SE"},
    "switzerland": {"name": "Switzerland", "code": "CH"},
    "united-kingdom": {"name": "United Kingdom", "code": "GB"},
}


class EventbriteScraper(BaseScraper):
    """Scraper for Eventbrite events via web scraping"""

    scraper_type = ScraperType.WEB

    BASE_URL = "https://www.eventbrite.com"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default rate limiting - will be overridden by params if provided
        self.min_delay = 2.0
        self.max_delay = 5.0

    def define_tables(self) -> List[Table]:
        """Define database tables for Eventbrite events"""
        events_table = Table(
            'events',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('event_id', String(100), unique=True, nullable=False),  # Eventbrite event ID
            Column('name', String(500), nullable=False),
            Column('description', Text),
            Column('url', String(1000), nullable=False),
            Column('start_date', String(255)),  # Stored as text from page
            Column('location', String(500)),
            Column('venue_name', String(500)),
            Column('city', String(255)),
            Column('country', String(100)),
            Column('country_code', String(5)),
            Column('status', String(100)),  # "Almost full", "Going fast", "Sales end soon", etc.
            Column('image_url', String(1000)),
            Column('is_online', Boolean, default=False),
            Column('scraped_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            extend_existing=True,
            schema=self.schema_name
        )
        return [events_table]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape events from Eventbrite

        Params:
            country: Country slug (e.g., "belgium", "france", "germany")
                     Use "all" to scrape all European countries
            cities: Optional list of city names to filter (e.g., ["brussels", "antwerp"])
            max_pages: Maximum number of pages to scrape per location (default: 5)
            min_delay: Minimum delay between requests in seconds (default: 2.0)
            max_delay: Maximum delay between requests in seconds (default: 5.0)
            categories: Optional list of categories to scrape (e.g., ["music", "food-and-drink"])

        Returns:
            List of event dictionaries
        """
        country = params.get('country', 'belgium')
        cities = params.get('cities', [])
        max_pages = params.get('max_pages', 5)
        min_delay = params.get('min_delay', self.min_delay)
        max_delay = params.get('max_delay', self.max_delay)
        categories = params.get('categories', [])

        self.log(f"Starting Eventbrite scrape with params: {params}")
        self.log(f"Rate limiting: random delay between {min_delay}s and {max_delay}s per request")

        # Determine which countries to scrape
        countries_to_scrape = []
        if country.lower() == "all":
            countries_to_scrape = list(EUROPEAN_COUNTRIES.keys())
            self.log(f"Scraping all {len(countries_to_scrape)} European countries")
        elif country.lower() in EUROPEAN_COUNTRIES:
            countries_to_scrape = [country.lower()]
        else:
            self.log(f"Unknown country: {country}. Available: {', '.join(EUROPEAN_COUNTRIES.keys())}", level="error")
            raise ValueError(f"Unknown country: {country}")

        all_events = []
        seen_event_ids = set()

        for country_slug in countries_to_scrape:
            country_info = EUROPEAN_COUNTRIES[country_slug]
            self.log(f"Scraping {country_info['name']} ({country_info['code']})...")

            # Build URLs to scrape
            urls_to_scrape = []

            # If cities specified, scrape city-specific pages
            if cities:
                for city in cities:
                    city_slug = city.lower().replace(' ', '-')
                    base_url = f"{self.BASE_URL}/d/{country_slug}--{city_slug}/events/"
                    urls_to_scrape.append((base_url, city, country_info))
            else:
                # Scrape country-level page
                base_url = f"{self.BASE_URL}/d/{country_slug}/events/"
                urls_to_scrape.append((base_url, None, country_info))

            # Add category-specific URLs if specified
            if categories:
                for url, city, info in urls_to_scrape.copy():
                    for category in categories:
                        category_url = f"{url}{category}/"
                        urls_to_scrape.append((category_url, city, info))

            # Scrape each URL
            for base_url, city, country_info in urls_to_scrape:
                try:
                    events = await self._scrape_location(
                        base_url,
                        city,
                        country_info,
                        max_pages,
                        min_delay,
                        max_delay,
                        seen_event_ids
                    )
                    all_events.extend(events)
                except Exception as e:
                    self.log(f"Error scraping {base_url}: {str(e)}", level="error")
                    continue

        self.log(f"Scraping complete. Total unique events: {len(all_events)}")
        return all_events

    async def _scrape_location(
        self,
        base_url: str,
        city: Optional[str],
        country_info: Dict,
        max_pages: int,
        min_delay: float,
        max_delay: float,
        seen_event_ids: set
    ) -> List[Dict[str, Any]]:
        """Scrape events from a specific location URL"""

        location_str = f"{city}, {country_info['name']}" if city else country_info['name']
        self.log(f"Scraping {location_str}: {base_url}")

        events = []

        # For now, just scrape the first page
        # Pagination will be added if Eventbrite uses query params or page numbers
        try:
            # Rate limiting
            delay = random.uniform(min_delay, max_delay)
            self.log(f"Waiting {delay:.2f}s before request...")
            await asyncio.sleep(delay)

            # Fetch the page
            response = await self.http_client.get(base_url)
            response.raise_for_status()

            self.log(f"Fetched {base_url} (status: {response.status_code}, size: {len(response.text)} bytes)")

            # Parse HTML
            soup = await self.parse_html(response.text, parser="html.parser")

            # Find event cards
            # Eventbrite uses various div structures, we'll look for links with /e/ pattern
            event_links = soup.find_all('a', href=re.compile(r'/e/[^/]+-\d+'))

            self.log(f"Found {len(event_links)} event links on page")

            # Process event cards
            parsed_events = []
            for link in event_links:
                try:
                    event_data = self._parse_event_card(link, city, country_info)
                    if event_data and event_data['event_id'] not in seen_event_ids:
                        parsed_events.append(event_data)
                        seen_event_ids.add(event_data['event_id'])
                except Exception as e:
                    self.log(f"Error parsing event card: {str(e)}", level="warning")
                    continue

            events.extend(parsed_events)
            self.log(f"Parsed {len(parsed_events)} unique events from {location_str}")

        except httpx.HTTPStatusError as e:
            self.log(f"HTTP error fetching {base_url}: {e.response.status_code}", level="error")
        except Exception as e:
            self.log(f"Error scraping {base_url}: {str(e)}", level="error")

        return events

    def _parse_event_card(self, link_element, city: Optional[str], country_info: Dict) -> Optional[Dict[str, Any]]:
        """Parse an event card/link element"""

        # Extract URL and event ID
        url = link_element.get('href', '')
        if not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"

        # Extract event ID from URL (format: /e/event-name-123456789)
        event_id_match = re.search(r'/e/[^/]+-(\d+)', url)
        if not event_id_match:
            return None

        event_id = event_id_match.group(1)

        # Extract event name from link aria-label attribute or text
        # The aria-label usually has the clean event name
        name = link_element.get('aria-label', '')
        if not name:
            # Try direct text of the link (might be nested in spans)
            # Look for the first substantial text node
            name_parts = []
            for text in link_element.stripped_strings:
                if len(text) > 3:  # Ignore very short strings
                    name_parts.append(text)
                    if len(text) > 10:  # If we get a good-length string, use it
                        break
            name = name_parts[0] if name_parts else "Unknown Event"

        # Clean the name - remove common suffixes
        name = re.sub(r'(Save this event:|Share this event:|Check ticket price).*$', '', name).strip()

        # Try to find the card container (parent elements)
        card = link_element.find_parent(['div', 'article', 'section'])

        # Try to find additional data in the card
        start_date = None
        location = None
        venue_name = None
        status = None
        image_url = None

        if card:
            # Get all text elements to process them
            all_text_elements = []
            for elem in card.find_all(['p', 'div', 'span'], recursive=True):
                text = elem.get_text(separator=' ', strip=True)
                if text and len(text) < 300:  # Skip very long text blocks
                    all_text_elements.append((elem, text))

            # Look for status badges (these come first usually)
            status_keywords = ['Almost full', 'Going fast', 'Sales end soon', 'Free', 'Online', 'Sold out']
            for elem, text in all_text_elements:
                if text in status_keywords:
                    status = text
                    if text == 'Online':
                        location = 'Online'
                    break

            # Look for date/time
            # Patterns: "Tomorrow • 11:00 PM", "Thu, Nov 20 • 2:00 PM", "Sat, Nov 29 •  8:00 PM"
            for elem, text in all_text_elements:
                if '•' in text and re.search(r'\d+:\d+\s*(AM|PM|am|pm)', text):
                    # This looks like a date/time string
                    # Extract the date pattern: starts with day/date, has •, ends with time
                    # Match patterns like: "Tomorrow • 11:00 PM" or "Thu, Nov 20 • 2:00 PM"
                    date_match = re.search(r'((?:Today|Tomorrow|Mon|Tue|Wed|Thu|Fri|Sat|Sun)[^•]*•\s*\d+:\d+\s*[APMapm]{2})', text, re.IGNORECASE)
                    if date_match:
                        start_date = date_match.group(1).strip()
                        break
                    # If no match, try simpler pattern
                    date_match = re.search(r'([^<>]*?\d+:\d+\s*[APMapm]{2})', text)
                    if date_match:
                        candidate = date_match.group(1).strip()
                        # Clean up - remove event name if it appears
                        if name and name in candidate:
                            candidate = candidate.replace(name, '').strip()
                        if len(candidate) < 100:  # Reasonable length
                            start_date = candidate
                            break

            # Look for venue/location
            # Usually appears after the date, before status badges
            # Look for relatively short text (< 100 chars) that's not the event name or date
            for elem, text in all_text_elements:
                # Skip if it's the name, date, status, or contains button text
                skip_keywords = ['Save this', 'Share this', 'Check ticket', 'Price', 'Ticket',
                                 'Almost full', 'Going fast', 'Sales end', 'Free', 'Online', name]
                if any(keyword.lower() in text.lower() for keyword in skip_keywords):
                    continue

                # Skip if it contains time format
                if re.search(r'\d+:\d+\s*(AM|PM)', text):
                    continue

                # If it's a reasonable length and doesn't look like the event name
                if 3 < len(text) < 100 and text != name:
                    # First one is likely the venue
                    if not venue_name:
                        venue_name = text
                        if not location:
                            location = text
                        break

            # Look for image
            img = card.find('img')
            if img:
                image_url = img.get('src')
                # Eventbrite often uses data-src for lazy loading
                if not image_url:
                    image_url = img.get('data-src')

        return {
            'event_id': event_id,
            'name': name,
            'url': url,
            'start_date': start_date,
            'location': location,
            'venue_name': venue_name,
            'city': city,
            'country': country_info['name'],
            'country_code': country_info['code'],
            'status': status,
            'image_url': image_url,
            'is_online': location == 'Online' if location else False,
            'scraped_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

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
    scraper = EventbriteScraper(
        scraper_id=999,
        schema_name="scraper_test",
        config={}
    )

    try:
        params = {
            'country': 'belgium',
            'max_pages': 1,
            'min_delay': 2.0,
            'max_delay': 3.0
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
            print(f"   Date: {event.get('start_date', 'N/A')}")
            print(f"   Location: {event.get('location', 'N/A')}")
            print(f"   URL: {event['url']}")

        print(f"\n{'='*80}")
        print("LOGS:")
        print(f"{'='*80}")
        print(scraper.get_logs())

    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

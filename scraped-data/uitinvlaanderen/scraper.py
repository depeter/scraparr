#!/usr/bin/env python3
"""
UiTinVlaanderen Event Scraper

Scrapes events from UiTdatabank API (powers uitinvlaanderen.be)
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data model"""
    id: str
    name: str
    description: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    location_name: Optional[str]
    location_address: Optional[str]
    city: Optional[str]
    postal_code: Optional[str]
    organizer: Optional[str]
    price_info: Optional[str]
    event_type: Optional[str]
    url: Optional[str]
    image_url: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class UiTinVlaanderenScraper:
    """Scraper for UiTinVlaanderen events via UiTdatabank API"""

    BASE_URL = "https://search.uitdatabank.be"
    SEARCH_ENDPOINT = "/offers/"

    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 0.5):
        """
        Initialize scraper

        Args:
            api_key: Optional API key for authentication
            rate_limit_delay: Delay between requests in seconds
        """
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()

        # Set headers
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'UiTinVlaanderen-Scraper/1.0'
        }
        if api_key:
            headers['X-Api-Key'] = api_key

        self.session.headers.update(headers)

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request with rate limiting and error handling

        Args:
            url: URL to request
            params: Query parameters

        Returns:
            JSON response or None on error
        """
        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None

    def search_events(
        self,
        query: Optional[str] = None,
        region: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 30,
        start: int = 0,
        sort: str = "availableTo"
    ) -> Optional[Dict]:
        """
        Search for events

        Args:
            query: Free text search query
            region: Region filter (e.g., "Antwerpen", "Gent", "Brussel")
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            event_type: Event type (e.g., "concert", "festival", "theater")
            limit: Number of results per page (max 50)
            start: Pagination offset
            sort: Sort field (availableTo, created, modified)

        Returns:
            API response with events or None on error
        """
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"

        # Build query string using Lucene syntax
        query_parts = []

        if query:
            query_parts.append(f'text:"{query}"')

        if region:
            query_parts.append(f'address.*.addressLocality:"{region}"')

        if date_from and date_to:
            query_parts.append(f'dateRange:[{date_from}T00:00:00Z TO {date_to}T23:59:59Z]')
        elif date_from:
            query_parts.append(f'dateRange:[{date_from}T00:00:00Z TO *]')

        if event_type:
            query_parts.append(f'terms.label:"{event_type}"')

        # Combine query parts
        q = " AND ".join(query_parts) if query_parts else "*:*"

        params = {
            'q': q,
            'limit': min(limit, 50),  # API max is typically 50
            'start': start,
            'sort': sort,
            'embed': 'true'  # Get full event details
        }

        logger.info(f"Searching events with query: {q}")

        return self._make_request(url, params)

    def get_event_details(self, event_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific event

        Args:
            event_id: Event UUID

        Returns:
            Event details or None on error
        """
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}{event_id}"
        logger.info(f"Fetching event details: {event_id}")
        return self._make_request(url)

    def parse_event(self, event_data: Dict) -> Event:
        """
        Parse event data into Event object

        Args:
            event_data: Raw event data from API

        Returns:
            Event object
        """
        # Extract basic info
        event_id = event_data.get('@id', '').split('/')[-1]
        name = event_data.get('name', {})
        if isinstance(name, dict):
            name = name.get('nl', name.get('en', 'Unknown'))

        description = event_data.get('description', {})
        if isinstance(description, dict):
            description = description.get('nl', description.get('en', ''))

        # Extract dates
        calendar = event_data.get('calendarSummary', {})
        start_date = None
        end_date = None

        if 'startDate' in event_data:
            start_date = event_data['startDate']
        if 'endDate' in event_data:
            end_date = event_data['endDate']

        # Extract location
        location = event_data.get('location', {})
        location_name = location.get('name', {})
        if isinstance(location_name, dict):
            location_name = location_name.get('nl', location_name.get('en', ''))

        address = location.get('address', {})
        location_address = address.get('streetAddress', '')
        city = address.get('addressLocality', '')
        postal_code = address.get('postalCode', '')

        # Extract organizer
        organizer_data = event_data.get('organizer', {})
        organizer = organizer_data.get('name', {})
        if isinstance(organizer, dict):
            organizer = organizer.get('nl', organizer.get('en', ''))

        # Extract price info
        price_info = None
        if 'priceInfo' in event_data:
            price_list = event_data['priceInfo']
            if price_list:
                price_info = price_list[0].get('name', {})
                if isinstance(price_info, dict):
                    price_info = price_info.get('nl', price_info.get('en', ''))

        # Extract event type
        event_type = None
        if 'terms' in event_data:
            terms = event_data['terms']
            if terms:
                event_type_data = terms[0].get('label', '')
                event_type = event_type_data

        # Extract URLs
        url = f"https://www.uitinvlaanderen.be/agenda/e/{event_id}"

        image_url = None
        if 'image' in event_data:
            image_url = event_data['image']
        elif 'mediaObject' in event_data and event_data['mediaObject']:
            image_url = event_data['mediaObject'][0].get('contentUrl', '')

        return Event(
            id=event_id,
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            location_name=location_name,
            location_address=location_address,
            city=city,
            postal_code=postal_code,
            organizer=organizer,
            price_info=price_info,
            event_type=event_type,
            url=url,
            image_url=image_url
        )

    def scrape_events(
        self,
        max_results: int = 100,
        **search_params
    ) -> List[Event]:
        """
        Scrape events with pagination

        Args:
            max_results: Maximum number of events to scrape
            **search_params: Parameters to pass to search_events()

        Returns:
            List of Event objects
        """
        events = []
        start = 0
        limit = 30

        while len(events) < max_results:
            # Search events
            response = self.search_events(
                start=start,
                limit=limit,
                **search_params
            )

            if not response:
                logger.warning("No response from API")
                break

            # Extract events from response
            items = response.get('member', [])

            if not items:
                logger.info("No more events found")
                break

            # Parse events
            for item in items:
                if len(events) >= max_results:
                    break

                try:
                    event = self.parse_event(item)
                    events.append(event)
                    logger.info(f"Scraped event: {event.name}")
                except Exception as e:
                    logger.error(f"Error parsing event: {e}")
                    continue

            # Check if there are more results
            total_items = response.get('totalItems', 0)
            if start + limit >= total_items:
                logger.info(f"Reached end of results (total: {total_items})")
                break

            start += limit

        logger.info(f"Scraped {len(events)} events")
        return events

    def save_events(self, events: List[Event], filename: str = "events.json"):
        """
        Save events to JSON file

        Args:
            events: List of Event objects
            filename: Output filename
        """
        data = [event.to_dict() for event in events]

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(events)} events to {filename}")


def main():
    """Example usage"""
    # Initialize scraper
    scraper = UiTinVlaanderenScraper(rate_limit_delay=0.5)

    # Example 1: Search for concerts in Antwerpen
    print("\n=== Searching for concerts in Antwerpen ===")
    events = scraper.scrape_events(
        max_results=10,
        query="concert",
        region="Antwerpen"
    )

    # Display results
    for event in events:
        print(f"\n{event.name}")
        print(f"  Location: {event.city}")
        print(f"  Date: {event.start_date}")
        print(f"  URL: {event.url}")

    # Save to file
    scraper.save_events(events, "concerts_antwerpen.json")

    # Example 2: Search for upcoming events this week
    print("\n\n=== Searching for events this week ===")
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    events = scraper.scrape_events(
        max_results=20,
        date_from=today,
        date_to=next_week
    )

    scraper.save_events(events, "events_this_week.json")
    print(f"\nScraped {len(events)} events this week")


if __name__ == "__main__":
    main()

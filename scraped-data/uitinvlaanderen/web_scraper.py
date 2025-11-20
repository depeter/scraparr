#!/usr/bin/env python3
"""
UiTinVlaanderen Web Scraper (Browser-based)

Alternative scraper that works by parsing the actual website HTML
when API access is not available.
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
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
    organizer: Optional[str]
    price_info: Optional[str]
    event_type: Optional[str]
    url: Optional[str]
    image_url: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class WebBasedScraper:
    """Web-based scraper for UiTinVlaanderen (no API key needed)"""

    BASE_URL = "https://www.uitinvlaanderen.be"

    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize web scraper

        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'nl,en;q=0.9',
        })

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """
        Make HTTP request with rate limiting

        Args:
            url: URL to request
            params: Query parameters

        Returns:
            HTML content or None on error
        """
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def extract_json_ld(self, html: str) -> List[Dict]:
        """
        Extract JSON-LD structured data from HTML

        Args:
            html: HTML content

        Returns:
            List of JSON-LD objects
        """
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(json_ld_pattern, html, re.DOTALL)

        results = []
        for match in matches:
            try:
                data = json.loads(match)
                results.append(data)
            except json.JSONDecodeError:
                continue

        return results

    def extract_events_from_page(self, html: str) -> List[Dict]:
        """
        Extract event data from page HTML

        Args:
            html: HTML content

        Returns:
            List of event data dictionaries
        """
        events = []

        # Look for JSON-LD structured data (best option)
        json_ld_data = self.extract_json_ld(html)
        for item in json_ld_data:
            if isinstance(item, dict) and item.get('@type') in ['Event', 'EventSeries']:
                events.append(item)

        # Look for embedded JSON data in script tags
        json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
        matches = re.findall(json_pattern, html, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                # Extract events from the state object
                if 'offers' in data:
                    offers = data['offers']
                    if isinstance(offers, dict) and 'items' in offers:
                        events.extend(offers['items'])
                    elif isinstance(offers, list):
                        events.extend(offers)
            except json.JSONDecodeError:
                continue

        return events

    def parse_event(self, event_data: Dict) -> Optional[Event]:
        """
        Parse event data into Event object

        Args:
            event_data: Raw event data (JSON-LD or API format)

        Returns:
            Event object or None if parsing fails
        """
        try:
            # Handle JSON-LD format
            if '@type' in event_data and event_data['@type'] in ['Event', 'EventSeries']:
                event_id = event_data.get('identifier', event_data.get('@id', '')).split('/')[-1]
                name = event_data.get('name', 'Unknown')
                description = event_data.get('description', '')

                # Extract dates
                start_date = event_data.get('startDate', '')
                end_date = event_data.get('endDate', '')

                # Extract location
                location = event_data.get('location', {})
                if isinstance(location, dict):
                    location_name = location.get('name', '')
                    address = location.get('address', {})
                    if isinstance(address, dict):
                        location_address = address.get('streetAddress', '')
                        city = address.get('addressLocality', '')
                    else:
                        location_address = ''
                        city = ''
                else:
                    location_name = str(location)
                    location_address = ''
                    city = ''

                # Extract organizer
                organizer_data = event_data.get('organizer', {})
                organizer = organizer_data.get('name', '') if isinstance(organizer_data, dict) else str(organizer_data)

                # Extract price
                offers = event_data.get('offers', {})
                price_info = None
                if isinstance(offers, dict):
                    price_info = offers.get('price', offers.get('name', ''))
                elif isinstance(offers, list) and offers:
                    price_info = offers[0].get('price', offers[0].get('name', ''))

                # Extract image
                image_url = event_data.get('image', '')

                # Extract event type
                event_type = event_data.get('genre', event_data.get('eventType', ''))

                url = event_data.get('url', f"{self.BASE_URL}/agenda/e/{event_id}")

            # Handle API/state format
            else:
                event_id = event_data.get('@id', event_data.get('id', '')).split('/')[-1]

                name = event_data.get('name', {})
                if isinstance(name, dict):
                    name = name.get('nl', name.get('en', 'Unknown'))

                description = event_data.get('description', {})
                if isinstance(description, dict):
                    description = description.get('nl', description.get('en', ''))

                start_date = event_data.get('startDate', '')
                end_date = event_data.get('endDate', '')

                location = event_data.get('location', {})
                location_name = location.get('name', {})
                if isinstance(location_name, dict):
                    location_name = location_name.get('nl', location_name.get('en', ''))

                address = location.get('address', {})
                location_address = address.get('streetAddress', '')
                city = address.get('addressLocality', '')

                organizer_data = event_data.get('organizer', {})
                organizer = organizer_data.get('name', {})
                if isinstance(organizer, dict):
                    organizer = organizer.get('nl', organizer.get('en', ''))

                price_info = None
                if 'priceInfo' in event_data:
                    price_list = event_data['priceInfo']
                    if price_list:
                        price_info = price_list[0].get('name', {})
                        if isinstance(price_info, dict):
                            price_info = price_info.get('nl', price_info.get('en', ''))

                event_type = None
                if 'terms' in event_data and event_data['terms']:
                    event_type = event_data['terms'][0].get('label', '')

                image_url = event_data.get('image', '')
                if not image_url and 'mediaObject' in event_data and event_data['mediaObject']:
                    image_url = event_data['mediaObject'][0].get('contentUrl', '')

                url = f"{self.BASE_URL}/agenda/e/{event_id}"

            return Event(
                id=event_id,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location_name=location_name,
                location_address=location_address,
                city=city,
                organizer=organizer,
                price_info=price_info,
                event_type=event_type,
                url=url,
                image_url=image_url
            )

        except Exception as e:
            logger.error(f"Error parsing event: {e}")
            return None

    def scrape_agenda_page(self, url: Optional[str] = None) -> List[Event]:
        """
        Scrape events from agenda page

        Args:
            url: Custom URL to scrape (defaults to main agenda page)

        Returns:
            List of Event objects
        """
        if url is None:
            url = f"{self.BASE_URL}/agenda"

        logger.info(f"Scraping: {url}")
        html = self._make_request(url)

        if not html:
            logger.error("Failed to fetch page")
            return []

        # Extract event data
        event_data_list = self.extract_events_from_page(html)
        logger.info(f"Found {len(event_data_list)} events in page")

        # Parse events
        events = []
        for event_data in event_data_list:
            event = self.parse_event(event_data)
            if event:
                events.append(event)
                logger.info(f"Scraped: {event.name}")

        return events

    def scrape_event_detail(self, event_id: str) -> Optional[Event]:
        """
        Scrape detailed information for a specific event

        Args:
            event_id: Event UUID

        Returns:
            Event object or None
        """
        url = f"{self.BASE_URL}/agenda/e/{event_id}"
        logger.info(f"Scraping event detail: {event_id}")

        html = self._make_request(url)
        if not html:
            return None

        # Extract event data
        event_data_list = self.extract_events_from_page(html)

        if event_data_list:
            return self.parse_event(event_data_list[0])

        return None

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
    scraper = WebBasedScraper(rate_limit_delay=1.0)

    # Scrape main agenda page
    print("\n=== Scraping main agenda page ===")
    events = scraper.scrape_agenda_page()

    # Display results
    print(f"\nFound {len(events)} events:")
    for event in events[:5]:  # Show first 5
        print(f"\n{event.name}")
        print(f"  Location: {event.city}")
        print(f"  Date: {event.start_date}")
        print(f"  URL: {event.url}")

    # Save to file
    if events:
        scraper.save_events(events, "web_scraped_events.json")
        print(f"\nSaved {len(events)} events to web_scraped_events.json")
    else:
        print("\nNo events found. The website structure may have changed.")
        print("Try inspecting the page source manually or use browser developer tools.")


if __name__ == "__main__":
    main()

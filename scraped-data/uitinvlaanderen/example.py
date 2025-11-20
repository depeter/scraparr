#!/usr/bin/env python3
"""
Example usage of UiTinVlaanderen scrapers
"""

import os
from datetime import datetime, timedelta
from scraper import UiTinVlaanderenScraper
from web_scraper import WebBasedScraper


def example_api_scraper():
    """Example usage of API-based scraper"""
    print("\n" + "="*60)
    print("API-BASED SCRAPER EXAMPLES")
    print("="*60)

    # Get API key from environment
    api_key = os.getenv('UITDATABANK_API_KEY')

    if not api_key:
        print("\n⚠️  No API key found!")
        print("Set your API key with: export UITDATABANK_API_KEY='your-key'")
        print("Or get one from: https://docs.publiq.be")
        return

    # Initialize scraper
    scraper = UiTinVlaanderenScraper(api_key=api_key, rate_limit_delay=1.0)

    # Example 1: Search for concerts
    print("\n1. Searching for concerts...")
    try:
        events = scraper.scrape_events(
            max_results=5,
            query="concert"
        )
        print(f"   Found {len(events)} concerts")
        if events:
            print(f"   First event: {events[0].name}")
            scraper.save_events(events, "api_concerts.json")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 2: Events in Antwerpen
    print("\n2. Searching for events in Antwerpen...")
    try:
        events = scraper.scrape_events(
            max_results=5,
            region="Antwerpen"
        )
        print(f"   Found {len(events)} events")
        if events:
            for event in events[:3]:
                print(f"   - {event.name} ({event.city})")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 3: Events this week
    print("\n3. Searching for events this week...")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        events = scraper.scrape_events(
            max_results=10,
            date_from=today,
            date_to=next_week
        )
        print(f"   Found {len(events)} events this week")
        if events:
            scraper.save_events(events, "api_events_this_week.json")
            print(f"   Saved to api_events_this_week.json")
    except Exception as e:
        print(f"   Error: {e}")


def example_web_scraper():
    """Example usage of web-based scraper"""
    print("\n" + "="*60)
    print("WEB-BASED SCRAPER EXAMPLES")
    print("="*60)
    print("\n⚠️  Note: Web scraper may have limitations due to")
    print("   client-side rendering. Use API scraper for best results.")

    # Initialize scraper
    scraper = WebBasedScraper(rate_limit_delay=2.0)

    # Example: Scrape main agenda page
    print("\n1. Scraping main agenda page...")
    try:
        events = scraper.scrape_agenda_page()
        print(f"   Found {len(events)} events")

        if events:
            print("\n   Sample events:")
            for event in events[:3]:
                print(f"   - {event.name}")
                print(f"     Location: {event.city or 'Unknown'}")
                print(f"     Date: {event.start_date or 'Unknown'}")

            scraper.save_events(events, "web_scraped_events.json")
            print(f"\n   Saved to web_scraped_events.json")
        else:
            print("   No events found (website may be client-side rendered)")
            print("   Consider using the API scraper instead")
    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Run examples"""
    print("\n" + "="*60)
    print("UiTinVlaanderen Scraper Examples")
    print("="*60)

    # Try API scraper first
    example_api_scraper()

    # Try web scraper
    example_web_scraper()

    print("\n" + "="*60)
    print("Done! Check the generated JSON files for results.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

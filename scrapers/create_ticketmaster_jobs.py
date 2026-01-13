#!/usr/bin/env python3
"""
Create weekly Ticketmaster scraping jobs for all European countries

This script creates scheduled jobs in Scraparr to scrape Ticketmaster events
from all European countries on a weekly basis, spread across the week.
"""

import requests
import json
import sys
import os

# Scraparr API base URL
API_BASE = os.getenv('SCRAPARR_API', 'http://scraparr:8000')

# Get auth token from environment
AUTH_TOKEN = os.getenv('SCRAPARR_AUTH_TOKEN')

# Get API key from environment or command line
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
if not TICKETMASTER_API_KEY and len(sys.argv) > 1:
    TICKETMASTER_API_KEY = sys.argv[1]

if not TICKETMASTER_API_KEY:
    print("Error: TICKETMASTER_API_KEY not provided")
    print("Usage:")
    print("  export TICKETMASTER_API_KEY=your_key_here")
    print("  export SCRAPARR_AUTH_TOKEN=your_token_here  # Optional")
    print("  python create_ticketmaster_jobs.py")
    print("Or:")
    print("  python create_ticketmaster_jobs.py your_key_here")
    sys.exit(1)

# Get scraper ID from command line or default to 4
SCRAPER_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 4

# European countries with Ticketmaster presence
# Organized by day of week (Monday=1, Sunday=0)
COUNTRIES = [
    # Monday (day 1)
    {"name": "United Kingdom", "code": "GB", "day": 1, "hour": 1},
    {"name": "Ireland", "code": "IE", "day": 1, "hour": 2},
    {"name": "Germany", "code": "DE", "day": 1, "hour": 3},
    {"name": "France", "code": "FR", "day": 1, "hour": 4},

    # Tuesday (day 2)
    {"name": "Spain", "code": "ES", "day": 2, "hour": 1},
    {"name": "Italy", "code": "IT", "day": 2, "hour": 2},
    {"name": "Netherlands", "code": "NL", "day": 2, "hour": 3},
    {"name": "Belgium", "code": "BE", "day": 2, "hour": 4},

    # Wednesday (day 3)
    {"name": "Switzerland", "code": "CH", "day": 3, "hour": 1},
    {"name": "Austria", "code": "AT", "day": 3, "hour": 2},
    {"name": "Sweden", "code": "SE", "day": 3, "hour": 3},
    {"name": "Norway", "code": "NO", "day": 3, "hour": 4},

    # Thursday (day 4)
    {"name": "Denmark", "code": "DK", "day": 4, "hour": 1},
    {"name": "Finland", "code": "FI", "day": 4, "hour": 2},
    {"name": "Poland", "code": "PL", "day": 4, "hour": 3},
    {"name": "Czech Republic", "code": "CZ", "day": 4, "hour": 4},

    # Friday (day 5)
    {"name": "Portugal", "code": "PT", "day": 5, "hour": 1},
    {"name": "Greece", "code": "GR", "day": 5, "hour": 2},
    {"name": "Hungary", "code": "HU", "day": 5, "hour": 3},
    {"name": "Romania", "code": "RO", "day": 5, "hour": 4},

    # Saturday (day 6)
    {"name": "Croatia", "code": "HR", "day": 6, "hour": 1},
    {"name": "Bulgaria", "code": "BG", "day": 6, "hour": 2},
    {"name": "Turkey", "code": "TR", "day": 6, "hour": 3},
    {"name": "Iceland", "code": "IS", "day": 6, "hour": 4},
]

DAYS = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    0: "Sunday"
}

def create_job(country: dict):
    """Create a weekly job for a country"""

    job_data = {
        "scraper_id": SCRAPER_ID,
        "name": f"Ticketmaster - {country['name']} Weekly",
        "description": f"Weekly scrape of {country['name']} - {DAYS[country['day']]} at {country['hour']}:00 AM",
        "params": {
            "api_key": TICKETMASTER_API_KEY,
            "country_code": country['code'],
            "max_events": 5000,
            "size": 200,
            "min_delay": 0.5,
            "max_delay": 2.0
        },
        "schedule_type": "cron",
        "schedule_config": {
            "expression": f"0 {country['hour']} * * {country['day']}"
        },
        "is_active": True
    }

    try:
        headers = {"Content-Type": "application/json"}
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

        response = requests.post(
            f"{API_BASE}/api/jobs",
            json=job_data,
            headers=headers,
            timeout=10
        )

        if response.status_code in [200, 201]:
            job = response.json()
            print(f"✅ Created job for {country['name']} (ID: {job.get('id')})")
            return True
        else:
            print(f"❌ Failed to create job for {country['name']}: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error creating job for {country['name']}: {str(e)}")
        return False

def main():
    print("="*80)
    print("Ticketmaster Weekly Job Creator")
    print("="*80)
    print(f"API Base: {API_BASE}")
    print(f"Scraper ID: {SCRAPER_ID}")
    print(f"API Key: {TICKETMASTER_API_KEY[:10]}...{TICKETMASTER_API_KEY[-4:]}")
    print(f"Countries: {len(COUNTRIES)}")
    print("="*80)
    print()

    # Check if scraper exists
    try:
        headers = {}
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

        response = requests.get(f"{API_BASE}/api/scrapers/{SCRAPER_ID}", headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Error: Scraper ID {SCRAPER_ID} not found")
            print(f"   Please register the Ticketmaster scraper first:")
            print(f"   curl -X POST {API_BASE}/api/scrapers \\")
            print(f"     -H 'Content-Type: application/json' \\")
            print(f"     -d '{{")
            print(f'       "name": "Ticketmaster Events",')
            print(f'       "module_path": "ticketmaster_scraper",')
            print(f'       "class_name": "TicketmasterScraper"')
            print(f"     }}\'")
            sys.exit(1)

        scraper = response.json()
        print(f"✅ Found scraper: {scraper.get('name')}")
        print()

    except Exception as e:
        print(f"❌ Error checking scraper: {str(e)}")
        sys.exit(1)

    # Create jobs
    success_count = 0
    fail_count = 0

    for country in COUNTRIES:
        if create_job(country):
            success_count += 1
        else:
            fail_count += 1

    print()
    print("="*80)
    print(f"Jobs Created: {success_count}")
    print(f"Failed: {fail_count}")
    print("="*80)

    if success_count > 0:
        print()
        print("Next steps:")
        print(f"1. View jobs: {API_BASE}/api/jobs")
        print(f"2. Check Scraparr UI to see scheduled jobs")
        print(f"3. Jobs will run automatically at scheduled times")
        print()
        print("Schedule summary:")
        for day_num in range(1, 7):
            day_countries = [c['name'] for c in COUNTRIES if c['day'] == day_num]
            if day_countries:
                print(f"  {DAYS[day_num]}: {', '.join(day_countries)}")

if __name__ == "__main__":
    main()

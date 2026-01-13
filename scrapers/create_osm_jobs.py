#!/usr/bin/env python3
"""
Create OpenStreetMap scraping jobs for all European countries.
Staggered execution times to avoid overwhelming the Overpass API.
"""

import requests
import sys
from datetime import datetime

# API configuration
API_BASE_URL = "http://localhost:8000/api"
SCRAPER_ID = 11  # OpenStreetMap scraper

# All European countries supported by the OpenStreetMap scraper
EUROPEAN_COUNTRIES = [
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech-republic",
    "denmark", "estonia", "finland", "france", "germany", "greece",
    "hungary", "iceland", "ireland", "italy", "latvia", "lithuania",
    "luxembourg", "malta", "netherlands", "norway", "poland", "portugal",
    "romania", "slovakia", "slovenia", "spain", "sweden", "switzerland",
    "turkey", "united-kingdom"
]

# Country display names
COUNTRY_NAMES = {
    "austria": "Austria",
    "belgium": "Belgium",
    "bulgaria": "Bulgaria",
    "croatia": "Croatia",
    "cyprus": "Cyprus",
    "czech-republic": "Czech Republic",
    "denmark": "Denmark",
    "estonia": "Estonia",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "greece": "Greece",
    "hungary": "Hungary",
    "iceland": "Iceland",
    "ireland": "Ireland",
    "italy": "Italy",
    "latvia": "Latvia",
    "lithuania": "Lithuania",
    "luxembourg": "Luxembourg",
    "malta": "Malta",
    "netherlands": "Netherlands",
    "norway": "Norway",
    "poland": "Poland",
    "portugal": "Portugal",
    "romania": "Romania",
    "slovakia": "Slovakia",
    "slovenia": "Slovenia",
    "spain": "Spain",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "turkey": "Turkey",
    "united-kingdom": "United Kingdom"
}


def get_auth_token(username="admin", password="admin123"):
    """Authenticate and get JWT token."""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_existing_jobs(token):
    """Get all existing jobs for OpenStreetMap scraper."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE_URL}/jobs",
        params={"scraper_id": SCRAPER_ID},
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def create_job(token, country, hour, day_of_month=1):
    """
    Create a monthly scheduled job for a country.

    Args:
        token: JWT auth token
        country: Country slug (e.g., "france")
        hour: Hour of day (UTC) to run the job (0-23)
        day_of_month: Day of month to run (default: 1st)
    """
    country_name = COUNTRY_NAMES[country]

    job_data = {
        "scraper_id": SCRAPER_ID,
        "name": f"OpenStreetMap - {country_name} Monthly",
        "description": f"Monthly scrape of {country_name} POIs from OpenStreetMap",
        "schedule_type": "cron",
        "schedule_config": {
            "expression": f"0 {hour} {day_of_month} * *"  # minute hour day-of-month month day-of-week
        },
        "params": {
            "country": country,
            "min_delay": 2.0,
            "max_delay": 4.0
        },
        "is_active": True
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{API_BASE_URL}/jobs",
        json=job_data,
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def main():
    """Create jobs for all European countries with staggered execution times."""

    print("OpenStreetMap Job Creation Script")
    print("=" * 70)
    print()

    # Authenticate
    print("Authenticating...")
    try:
        token = get_auth_token()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)

    # Get existing jobs
    print("\nChecking existing jobs...")
    try:
        existing_jobs = get_existing_jobs(token)
        existing_countries = set()
        for job in existing_jobs:
            if job.get("params", {}).get("country"):
                existing_countries.add(job["params"]["country"])
        print(f"✓ Found {len(existing_jobs)} existing OpenStreetMap jobs")
        if existing_countries:
            print(f"  Existing countries: {', '.join(sorted(existing_countries))}")
    except Exception as e:
        print(f"✗ Failed to fetch existing jobs: {e}")
        existing_countries = set()

    # Create jobs with staggered times
    print("\nCreating jobs for all European countries...")
    print("(Staggered across hours 0-23 UTC to distribute load)")
    print()

    created = 0
    skipped = 0
    failed = 0

    # Distribute countries across 24 hours (some hours will have multiple countries)
    countries_per_hour = (len(EUROPEAN_COUNTRIES) + 23) // 24

    for i, country in enumerate(sorted(EUROPEAN_COUNTRIES)):
        # Skip if job already exists for this country
        if country in existing_countries:
            print(f"⊘ {COUNTRY_NAMES[country]:20s} - Job already exists, skipping")
            skipped += 1
            continue

        # Assign hour (distribute countries evenly across 24 hours)
        hour = (i // countries_per_hour) % 24
        cron_expr = f"0 {hour} 1 * *"

        try:
            job = create_job(token, country, hour)
            job_id = job.get("id", "?")
            print(f"✓ {COUNTRY_NAMES[country]:20s} - Created job #{job_id} (runs {cron_expr} UTC)")
            created += 1
        except Exception as e:
            print(f"✗ {COUNTRY_NAMES[country]:20s} - Failed: {e}")
            failed += 1

    # Summary
    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Created: {created}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {len(EUROPEAN_COUNTRIES)}")
    print()

    if created > 0:
        print("Jobs created successfully! They will run on the 1st of each month.")
        print("Execution times are staggered across different hours to distribute load.")
        print()
        print("Next steps:")
        print("  - Monitor executions via: GET /api/executions?scraper_id=11")
        print("  - View jobs via: GET /api/jobs?scraper_id=11")
        print("  - Verify data in database: scraper_11.pois table")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Update OpenStreetMap jobs to run bi-monthly (every 2 months)
with schedules spread across different days and months.
"""

import requests
import sys

# API configuration
API_BASE_URL = "http://localhost:8000/api"
SCRAPER_ID = 11  # OpenStreetMap scraper

# All European countries (same order as creation)
EUROPEAN_COUNTRIES = [
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech-republic",
    "denmark", "estonia", "finland", "france", "germany", "greece",
    "hungary", "iceland", "ireland", "italy", "latvia", "lithuania",
    "luxembourg", "malta", "netherlands", "norway", "poland", "portugal",
    "romania", "slovakia", "slovenia", "spain", "sweden", "switzerland",
    "turkey", "united-kingdom"
]


def get_auth_token(username="admin", password="admin123"):
    """Authenticate and get JWT token."""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_osm_jobs(token):
    """Get all OpenStreetMap jobs."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE_URL}/jobs",
        params={"scraper_id": SCRAPER_ID},
        headers=headers
    )
    response.raise_for_status()
    data = response.json()

    # Handle both list response and paginated response
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    return data


def update_job_schedule(token, job_id, cron_expression, job_name):
    """Update a job's schedule."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.put(
        f"{API_BASE_URL}/jobs/{job_id}",
        json={
            "schedule_config": {"expression": cron_expression}
        },
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def main():
    """Update all OSM jobs to bi-monthly schedules."""

    print("OpenStreetMap Job Update Script - Bi-Monthly Scheduling")
    print("=" * 70)
    print()
    print("Strategy:")
    print("  - Half of countries run in ODD months (1,3,5,7,9,11)")
    print("  - Half of countries run in EVEN months (2,4,6,8,10,12)")
    print("  - Spread across days 1-31 of the month")
    print("  - Spread across hours 0-23 UTC")
    print()

    # Authenticate
    print("Authenticating...")
    try:
        token = get_auth_token()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)

    # Get jobs
    print("\nFetching OpenStreetMap jobs...")
    try:
        jobs = get_osm_jobs(token)
        print(f"✓ Found {len(jobs)} OpenStreetMap jobs")
    except Exception as e:
        print(f"✗ Failed to fetch jobs: {e}")
        sys.exit(1)

    # Create country -> job mapping
    country_jobs = {}
    for job in jobs:
        country = job.get("params", {}).get("country")
        if country:
            country_jobs[country] = job

    print(f"\nMapped {len(country_jobs)} jobs to countries")
    print()

    # Update schedules
    print("Updating job schedules...")
    print()

    updated = 0
    failed = 0

    # We have 32 countries to distribute
    # Distribute across:
    # - 2 month groups (odd/even)
    # - 16 days (1-16)
    # - 2 hours per day (0-1, 2-3, etc.)

    for i, country in enumerate(sorted(EUROPEAN_COUNTRIES)):
        if country not in country_jobs:
            print(f"⊘ {country:20s} - Job not found, skipping")
            continue

        job = country_jobs[country]
        job_id = job["id"]

        # Alternate between odd and even months
        if i % 2 == 0:
            months = "1,3,5,7,9,11"  # Odd months
            month_label = "odd"
        else:
            months = "2,4,6,8,10,12"  # Even months
            month_label = "even"

        # Spread across days 1-16 (2 countries per day)
        day = (i // 2) % 16 + 1

        # Spread across hours 0-23 (cycle through)
        hour = i % 24

        # Create cron expression: minute hour day month day-of-week
        cron_expr = f"0 {hour} {day} {months} *"

        try:
            update_job_schedule(token, job_id, cron_expr, job["name"])
            print(f"✓ {country:20s} - Job #{job_id:3d} → {cron_expr:20s} ({month_label} months, day {day:2d}, hour {hour:2d})")
            updated += 1
        except Exception as e:
            print(f"✗ {country:20s} - Failed: {e}")
            failed += 1

    # Summary
    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Updated: {updated}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {len(EUROPEAN_COUNTRIES)}")
    print()

    if updated > 0:
        print("Jobs updated successfully!")
        print()
        print("Schedule distribution:")
        print("  - ODD months (Jan,Mar,May,Jul,Sep,Nov): 16 countries")
        print("  - EVEN months (Feb,Apr,Jun,Aug,Oct,Dec): 16 countries")
        print("  - Days: Spread across 1-16 of each month")
        print("  - Hours: Distributed 0-23 UTC")
        print()
        print("This means:")
        print("  - Maximum 2 countries run per day")
        print("  - Each country runs every 2 months")
        print("  - Load is distributed across entire month")
        print()
        print("Next steps:")
        print("  - View updated jobs: GET /api/jobs?scraper_id=11")
        print("  - Monitor executions: GET /api/executions?scraper_id=11")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

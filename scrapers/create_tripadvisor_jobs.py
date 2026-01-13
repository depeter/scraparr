#!/usr/bin/env python3
"""
Create scheduled jobs for TripAdvisor scraper across European countries

This script creates weekly scheduled jobs for scraping TripAdvisor
attractions, restaurants, and hotels from major European cities.

Usage:
    python create_tripadvisor_jobs.py

Requirements:
    - Scraparr backend must be running
    - TripAdvisor scraper must be registered (scraper_id needed)
"""

import requests
import json
from datetime import datetime

# Scraparr API URL - adjust if needed
API_BASE_URL = "http://localhost:8000/api"

# Get auth token
AUTH_TOKEN = None  # Set if authentication is required

# TripAdvisor scraper configuration
# IMPORTANT: Update this after registering the scraper
TRIPADVISOR_SCRAPER_ID = None  # Will be set after checking/creating scraper

# European countries grouped by day for scheduling
# Each day scrapes different countries to spread the load
SCHEDULE = {
    # Monday: Western Europe
    "monday": [
        {"country": "france", "cron_hour": 1},
        {"country": "belgium", "cron_hour": 2},
        {"country": "netherlands", "cron_hour": 3},
        {"country": "united-kingdom", "cron_hour": 4},
    ],
    # Tuesday: Southern Europe
    "tuesday": [
        {"country": "spain", "cron_hour": 1},
        {"country": "italy", "cron_hour": 2},
        {"country": "portugal", "cron_hour": 3},
        {"country": "greece", "cron_hour": 4},
    ],
    # Wednesday: Central Europe
    "wednesday": [
        {"country": "germany", "cron_hour": 1},
        {"country": "austria", "cron_hour": 2},
        {"country": "switzerland", "cron_hour": 3},
        {"country": "czech-republic", "cron_hour": 4},
    ],
    # Thursday: Northern Europe
    "thursday": [
        {"country": "sweden", "cron_hour": 1},
        {"country": "norway", "cron_hour": 2},
        {"country": "denmark", "cron_hour": 3},
        {"country": "finland", "cron_hour": 4},
    ],
    # Friday: Eastern Europe
    "friday": [
        {"country": "poland", "cron_hour": 1},
        {"country": "hungary", "cron_hour": 2},
        {"country": "romania", "cron_hour": 3},
        {"country": "croatia", "cron_hour": 4},
    ],
    # Saturday: Remaining countries
    "saturday": [
        {"country": "ireland", "cron_hour": 1},
        {"country": "turkey", "cron_hour": 2},
        {"country": "iceland", "cron_hour": 3},
    ],
}

# Day of week mapping for cron (0 = Sunday, 1 = Monday, etc.)
DAY_OF_WEEK = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}

# Country display names
COUNTRY_NAMES = {
    "austria": "Austria",
    "belgium": "Belgium",
    "croatia": "Croatia",
    "czech-republic": "Czech Republic",
    "denmark": "Denmark",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "greece": "Greece",
    "hungary": "Hungary",
    "iceland": "Iceland",
    "ireland": "Ireland",
    "italy": "Italy",
    "netherlands": "Netherlands",
    "norway": "Norway",
    "poland": "Poland",
    "portugal": "Portugal",
    "romania": "Romania",
    "spain": "Spain",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "turkey": "Turkey",
    "united-kingdom": "United Kingdom",
}


def get_headers():
    """Get request headers including auth if needed"""
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return headers


def find_or_create_scraper():
    """Find existing TripAdvisor scraper or create a new one"""
    global TRIPADVISOR_SCRAPER_ID

    print("Checking for existing TripAdvisor scraper...")

    # List existing scrapers
    try:
        response = requests.get(f"{API_BASE_URL}/scrapers", headers=get_headers())
        if response.status_code == 200:
            scrapers = response.json()
            for scraper in scrapers:
                if "tripadvisor" in scraper.get("name", "").lower() or \
                   "tripadvisor" in scraper.get("module_path", "").lower():
                    TRIPADVISOR_SCRAPER_ID = scraper["id"]
                    print(f"Found existing TripAdvisor scraper with ID: {TRIPADVISOR_SCRAPER_ID}")
                    return True
    except Exception as e:
        print(f"Error checking scrapers: {e}")

    # Create new scraper if not found
    print("Creating new TripAdvisor scraper...")

    scraper_data = {
        "name": "TripAdvisor Europe",
        "description": "Scrapes attractions, restaurants, and hotels from TripAdvisor for European countries",
        "scraper_type": "web",
        "module_path": "tripadvisor_scraper",
        "class_name": "TripAdvisorScraper",
        "config": {
            "min_delay": 3.0,
            "max_delay": 8.0,
        },
        "headers": {},
        "is_active": True,
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/scrapers",
            json=scraper_data,
            headers=get_headers()
        )

        if response.status_code in [200, 201]:
            result = response.json()
            TRIPADVISOR_SCRAPER_ID = result["id"]
            print(f"Created TripAdvisor scraper with ID: {TRIPADVISOR_SCRAPER_ID}")
            print(f"Schema: {result.get('schema_name', 'N/A')}")
            return True
        else:
            print(f"Failed to create scraper: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"Error creating scraper: {e}")
        return False


def create_job(country: str, day: str, hour: int, category: str = "attractions"):
    """Create a single job for a country/category combination"""

    day_num = DAY_OF_WEEK[day]
    country_name = COUNTRY_NAMES.get(country, country.title())

    job_data = {
        "scraper_id": TRIPADVISOR_SCRAPER_ID,
        "name": f"TripAdvisor - {country_name} {category.title()} Weekly",
        "description": f"Weekly scrape of {category} in {country_name} - {day.title()} at {hour}:00 AM UTC",
        "params": {
            "country": country,
            "category": category,
            "max_results": 500,
            "include_reviews": False,
            "min_delay": 3.0,
            "max_delay": 8.0,
            "resume": True,
        },
        "schedule_type": "cron",
        "schedule_config": {
            "expression": f"0 {hour} * * {day_num}"  # minute hour day_of_month month day_of_week
        },
        "is_active": True,
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/jobs",
            json=job_data,
            headers=get_headers()
        )

        if response.status_code in [200, 201]:
            result = response.json()
            print(f"  [OK] Created job: {job_data['name']} (ID: {result['id']})")
            return True
        else:
            print(f"  [FAIL] {job_data['name']}: {response.status_code}")
            if response.text:
                print(f"         {response.text[:200]}")
            return False

    except Exception as e:
        print(f"  [ERROR] {job_data['name']}: {e}")
        return False


def create_all_jobs(categories=None):
    """Create jobs for all scheduled countries"""

    if categories is None:
        categories = ["attractions"]  # Start with attractions only

    print(f"\nCreating jobs for categories: {', '.join(categories)}")
    print("=" * 60)

    total_created = 0
    total_failed = 0

    for day, countries in SCHEDULE.items():
        print(f"\n{day.upper()}:")
        print("-" * 40)

        for country_config in countries:
            country = country_config["country"]
            hour = country_config["cron_hour"]

            for category in categories:
                if create_job(country, day, hour, category):
                    total_created += 1
                else:
                    total_failed += 1

                # Offset hour for different categories
                hour += 1

    print("\n" + "=" * 60)
    print(f"SUMMARY: Created {total_created} jobs, {total_failed} failed")
    print("=" * 60)


def list_existing_jobs():
    """List existing TripAdvisor jobs"""
    print("\nExisting TripAdvisor jobs:")
    print("-" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/jobs", headers=get_headers())
        if response.status_code == 200:
            jobs = response.json()
            tripadvisor_jobs = [j for j in jobs if "tripadvisor" in j.get("name", "").lower()]

            if not tripadvisor_jobs:
                print("No TripAdvisor jobs found")
                return

            for job in tripadvisor_jobs:
                status = "ACTIVE" if job.get("is_active") else "PAUSED"
                schedule = job.get("schedule_config", {}).get("expression", "N/A")
                print(f"  [{status}] {job['name']}")
                print(f"           Schedule: {schedule}")
                print(f"           Next run: {job.get('next_run_at', 'N/A')}")

    except Exception as e:
        print(f"Error listing jobs: {e}")


def delete_all_tripadvisor_jobs():
    """Delete all existing TripAdvisor jobs (use with caution!)"""
    print("\nDeleting all TripAdvisor jobs...")

    try:
        response = requests.get(f"{API_BASE_URL}/jobs", headers=get_headers())
        if response.status_code == 200:
            jobs = response.json()
            tripadvisor_jobs = [j for j in jobs if "tripadvisor" in j.get("name", "").lower()]

            for job in tripadvisor_jobs:
                delete_response = requests.delete(
                    f"{API_BASE_URL}/jobs/{job['id']}",
                    headers=get_headers()
                )
                if delete_response.status_code in [200, 204]:
                    print(f"  [DELETED] {job['name']}")
                else:
                    print(f"  [FAILED] {job['name']}: {delete_response.status_code}")

    except Exception as e:
        print(f"Error deleting jobs: {e}")


def main():
    """Main entry point"""
    global API_BASE_URL, AUTH_TOKEN
    import argparse

    parser = argparse.ArgumentParser(description="Create TripAdvisor scraping jobs")
    parser.add_argument("--list", action="store_true", help="List existing TripAdvisor jobs")
    parser.add_argument("--delete-all", action="store_true", help="Delete all TripAdvisor jobs")
    parser.add_argument("--categories", nargs="+", default=["attractions"],
                        choices=["attractions", "restaurants", "hotels"],
                        help="Categories to scrape (default: attractions)")
    parser.add_argument("--api-url", default=API_BASE_URL, help="Scraparr API base URL")
    parser.add_argument("--token", help="Authentication token")

    args = parser.parse_args()

    API_BASE_URL = args.api_url
    AUTH_TOKEN = args.token

    print("=" * 60)
    print("TripAdvisor Job Creator for Scraparr")
    print("=" * 60)
    print(f"API URL: {API_BASE_URL}")
    print(f"Categories: {', '.join(args.categories)}")

    if args.list:
        list_existing_jobs()
        return

    if args.delete_all:
        confirm = input("Are you sure you want to delete ALL TripAdvisor jobs? (yes/no): ")
        if confirm.lower() == "yes":
            delete_all_tripadvisor_jobs()
        else:
            print("Cancelled")
        return

    # Find or create the scraper
    if not find_or_create_scraper():
        print("ERROR: Could not find or create TripAdvisor scraper")
        print("Please register the scraper manually first")
        return

    # Create jobs for all countries
    create_all_jobs(categories=args.categories)

    print("\nDone! Jobs will run according to their schedules.")
    print("Monitor executions at: http://localhost:3001/executions")


if __name__ == "__main__":
    main()

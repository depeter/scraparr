# UiTinVlaanderen Event Scraper

A Python web scraper for extracting event data from [UiTinVlaanderen.be](https://www.uitinvlaanderen.be), the Flemish cultural events platform. This scraper uses the UiTdatabank Search API to retrieve comprehensive event information.

**⚠️ Important:** The UiTdatabank API requires an API key for access. You need to register at [UiTdatabank](https://www.uitdatabank.be) to obtain an API key.

## Features

- Search events by keyword, region, date range, and event type
- Pagination support for scraping large result sets
- Rate limiting to be respectful to the API
- Structured data extraction (name, dates, location, organizer, prices, images)
- Export to JSON format
- Error handling and logging
- Flexible query building with Lucene syntax

## Prerequisites

### Getting an API Key

To use the API-based scraper (`scraper.py`), you need an API key:

1. Visit [UiTdatabank](https://www.uitdatabank.be) or [Publiq Developer Portal](https://docs.publiq.be)
2. Register for an account
3. Request API access for the Search API
4. You'll receive an API key (x-api-key)

### Alternative: Web Scraper (No API Key)

If you don't have an API key, you can use `web_scraper.py` which parses the website HTML directly. Note: This is more fragile and may break if the website structure changes. The website uses Vue.js client-side rendering, so event data is loaded dynamically via JavaScript.

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your API key (for API scraper):
```bash
export UITDATABANK_API_KEY="your-api-key-here"
```

## Usage

### API-Based Scraper (Recommended)

The API scraper (`scraper.py`) provides the most reliable and complete data:

```python
from scraper import UiTinVlaanderenScraper
import os

# Initialize scraper with API key
api_key = os.getenv('UITDATABANK_API_KEY')
scraper = UiTinVlaanderenScraper(api_key=api_key)

# Scrape events
events = scraper.scrape_events(max_results=50)

# Save to JSON
scraper.save_events(events, "events.json")
```

### Web-Based Scraper (No API Key)

The web scraper (`web_scraper.py`) is an alternative that doesn't require an API key:

```python
from web_scraper import WebBasedScraper

# Initialize scraper
scraper = WebBasedScraper()

# Scrape main agenda page
events = scraper.scrape_agenda_page()

# Save to JSON
scraper.save_events(events, "events.json")
```

**Note:** The web scraper may have limitations due to client-side rendering. For best results, use the API scraper with a valid API key.

### Search by Region

```python
# Search for events in Brussels
events = scraper.scrape_events(
    max_results=20,
    region="Brussel"
)
```

### Search by Date Range

```python
from datetime import datetime, timedelta

# Get events for the next 7 days
today = datetime.now().strftime("%Y-%m-%d")
next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

events = scraper.scrape_events(
    max_results=100,
    date_from=today,
    date_to=next_week
)
```

### Search by Keyword and Type

```python
# Search for concerts
events = scraper.scrape_events(
    max_results=30,
    query="jazz",
    event_type="concert"
)
```

### Combined Filters

```python
# Search for theater performances in Antwerp this month
events = scraper.scrape_events(
    max_results=50,
    query="theater",
    region="Antwerpen",
    date_from="2025-11-01",
    date_to="2025-11-30"
)
```

### Get Event Details

```python
# Get detailed information for a specific event
event_details = scraper.get_event_details(event_id="12345-abc-def")
```

## Running the Example Script

The scraper includes example usage in the `main()` function:

```bash
python scraper.py
```

This will:
1. Search for concerts in Antwerpen (10 results)
2. Search for events happening this week (20 results)
3. Save results to JSON files

## Data Structure

Each scraped event contains the following fields:

```python
{
    "id": "event-uuid",
    "name": "Event Name",
    "description": "Event description in Dutch or English",
    "start_date": "2025-11-15T20:00:00",
    "end_date": "2025-11-15T23:00:00",
    "location_name": "Venue Name",
    "location_address": "Street Address",
    "city": "City Name",
    "postal_code": "2000",
    "organizer": "Organizer Name",
    "price_info": "€15.00",
    "event_type": "Concert",
    "url": "https://www.uitinvlaanderen.be/agenda/e/event-uuid",
    "image_url": "https://..."
}
```

## API Parameters

### Search Parameters

- `query`: Free text search (searches in event name, description, etc.)
- `region`: Filter by city/municipality name (e.g., "Antwerpen", "Gent", "Brussel")
- `date_from`: Start date in YYYY-MM-DD format
- `date_to`: End date in YYYY-MM-DD format
- `event_type`: Event category (e.g., "concert", "festival", "theater")
- `limit`: Results per page (default: 30, max: 50)
- `start`: Pagination offset (default: 0)
- `sort`: Sort order (default: "availableTo")

### Scrape Parameters

- `max_results`: Maximum number of events to scrape (default: 100)
- `rate_limit_delay`: Delay between API requests in seconds (default: 0.5)

## Advanced Usage

### Custom Rate Limiting

```python
# Slower rate limiting (1 second between requests)
scraper = UiTinVlaanderenScraper(rate_limit_delay=1.0)
```

### With API Key (if available)

```python
# If you have an API key from UiTdatabank
scraper = UiTinVlaanderenScraper(api_key="your-api-key")
```

### Manual Pagination

```python
# Fetch specific page of results
response = scraper.search_events(
    query="festival",
    limit=30,
    start=60  # Skip first 60 results (page 3)
)
```

### Direct Lucene Query

The scraper builds Lucene queries automatically, but you can also construct them manually:

```python
# Complex query with multiple conditions
events = scraper.scrape_events(
    query='address.*.addressLocality:"Gent" AND terms.label:"concert" AND dateRange:[2025-11-01T00:00:00Z TO 2025-12-31T23:59:59Z]'
)
```

## Common Regions

Popular cities/regions in Flanders:

- Antwerpen
- Gent
- Brugge
- Leuven
- Mechelen
- Aalst
- Sint-Niklaas
- Hasselt
- Kortrijk
- Oostende
- Brussel (Brussels)

## Common Event Types

- concert
- festival
- theater
- tentoonstelling (exhibition)
- film
- cursus (course)
- sport
- party
- rondleiding (tour)

## Logging

The scraper uses Python's logging module. To adjust logging level:

```python
import logging

logging.basicConfig(level=logging.DEBUG)  # Show all messages
# or
logging.basicConfig(level=logging.WARNING)  # Show only warnings/errors
```

## Rate Limiting & Best Practices

- Default rate limit: 0.5 seconds between requests
- Be respectful to the API - don't scrape excessively
- Consider caching results if scraping frequently
- Use specific filters to reduce the number of requests

## Error Handling

The scraper includes comprehensive error handling:

- Network errors are logged and return `None`
- JSON decode errors are caught and logged
- Invalid event data is skipped with error logging
- HTTP errors (4xx, 5xx) raise exceptions

## API Documentation

This scraper uses the UiTdatabank Search API. For more information:

- [UiTdatabank Documentation](https://docs.publiq.be/docs/uitdatabank/search-api/introduction)
- [UiTinVlaanderen Website](https://www.uitinvlaanderen.be)

## License

This scraper is for educational and personal use. Please respect the UiTdatabank API terms of service and rate limits.

## Contributing

Contributions welcome! Please ensure:

1. Code follows PEP 8 style guidelines
2. Add appropriate error handling
3. Update documentation for new features
4. Test thoroughly before submitting

## Troubleshooting

### No events returned

- Check your search parameters (they might be too restrictive)
- Try a broader search first (e.g., no filters)
- Check the API is accessible: `curl https://search.uitdatabank.be/offers/`

### Rate limiting errors

- Increase `rate_limit_delay` parameter
- Reduce `max_results` for initial testing

### JSON decode errors

- The API might be returning HTML instead of JSON (check network/auth)
- Verify the API endpoint is still valid

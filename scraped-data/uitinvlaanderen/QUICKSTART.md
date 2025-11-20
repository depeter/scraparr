# Quick Start Guide

Get started scraping events from UiTinVlaanderen in under 5 minutes!

## Quick Setup

```bash
# 1. Navigate to the directory
cd /home/peter/scraparr/uitinvlaanderen

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Method 1: API Scraper (Best - Requires API Key)

### Get an API Key

See [API_KEY_GUIDE.md](API_KEY_GUIDE.md) for detailed instructions.

Quick summary:
1. Visit https://docs.publiq.be or https://www.publiq.be
2. Register for an account
3. Request API access
4. Receive your API key

### Use the Scraper

```bash
# Set your API key
export UITDATABANK_API_KEY="your-api-key-here"

# Run the example
python example.py
```

### Python Code Example

```python
from scraper import UiTinVlaanderenScraper
import os

# Initialize with API key
api_key = os.getenv('UITDATABANK_API_KEY')
scraper = UiTinVlaanderenScraper(api_key=api_key)

# Scrape events
events = scraper.scrape_events(
    max_results=10,
    region="Antwerpen",
    query="concert"
)

# Save to file
scraper.save_events(events, "my_events.json")

# Print results
for event in events:
    print(f"{event.name} - {event.city} - {event.start_date}")
```

## Method 2: Web Scraper (No API Key Needed)

**Note:** This method has limitations due to client-side rendering.

```python
from web_scraper import WebBasedScraper

# Initialize
scraper = WebBasedScraper()

# Scrape the main page
events = scraper.scrape_agenda_page()

# Save results
scraper.save_events(events, "web_events.json")
```

## Common Use Cases

### 1. Find Concerts in Your City

```python
events = scraper.scrape_events(
    max_results=20,
    event_type="concert",
    region="Gent"
)
```

### 2. Events This Weekend

```python
from datetime import datetime, timedelta

today = datetime.now()
weekend_start = today + timedelta(days=(5 - today.weekday()))
weekend_end = weekend_start + timedelta(days=2)

events = scraper.scrape_events(
    max_results=50,
    date_from=weekend_start.strftime("%Y-%m-%d"),
    date_to=weekend_end.strftime("%Y-%m-%d")
)
```

### 3. Search by Keyword

```python
events = scraper.scrape_events(
    max_results=30,
    query="jazz festival"
)
```

### 4. Get Event Details

```python
# Get details for a specific event
event = scraper.get_event_details("event-uuid-here")
```

## Output Format

Events are saved as JSON with this structure:

```json
[
  {
    "id": "event-uuid",
    "name": "Event Name",
    "description": "Full description...",
    "start_date": "2025-11-15T20:00:00",
    "end_date": "2025-11-15T23:00:00",
    "location_name": "Venue Name",
    "location_address": "Street Address",
    "city": "City",
    "postal_code": "2000",
    "organizer": "Organizer Name",
    "price_info": "€15.00",
    "event_type": "Concert",
    "url": "https://www.uitinvlaanderen.be/agenda/e/...",
    "image_url": "https://..."
  }
]
```

## Rate Limiting

The scraper includes built-in rate limiting:

```python
# Adjust delay between requests (default: 0.5 seconds)
scraper = UiTinVlaanderenScraper(
    api_key=api_key,
    rate_limit_delay=1.0  # 1 second between requests
)
```

## Troubleshooting

### "401 Unauthorized"
- Missing or invalid API key
- Set your API key: `export UITDATABANK_API_KEY="your-key"`

### "No events found"
- Filters may be too restrictive - try a broader search
- Check the website is accessible: https://www.uitinvlaanderen.be

### "Rate limit exceeded"
- Increase `rate_limit_delay`
- Reduce `max_results`
- Wait a few minutes before trying again

## Next Steps

- **Read the full documentation**: [README.md](README.md)
- **Get an API key**: [API_KEY_GUIDE.md](API_KEY_GUIDE.md)
- **Explore examples**: Run `python example.py`

## Need Help?

1. Check the [README.md](README.md) for detailed documentation
2. See [API_KEY_GUIDE.md](API_KEY_GUIDE.md) for API access help
3. Review the code in `scraper.py` and `web_scraper.py`
4. Check UiTdatabank documentation: https://docs.publiq.be

Happy scraping! 🎉

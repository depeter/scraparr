# TripAdvisor Scraper for Scraparr

Web scraper for TripAdvisor attractions, restaurants, and hotels in European countries.

## Overview

This scraper extracts Points of Interest (POIs) from TripAdvisor, including:
- **Attractions**: Museums, landmarks, tours, activities
- **Restaurants**: Dining establishments with cuisine types, price levels
- **Hotels**: Accommodations with star ratings and amenities

## Features

- **23 European Countries** supported with major cities pre-configured
- **Resume Capability**: Can continue from where it left off if interrupted
- **Rate Limiting**: Configurable delays to avoid being blocked
- **Deduplication**: Tracks seen IDs to avoid duplicate entries
- **Review Scraping**: Optional detailed review collection
- **Progress Tracking**: Saves progress to database for long-running jobs

## Supported Countries

| Country | Major Cities |
|---------|-------------|
| Austria | Vienna, Salzburg, Innsbruck |
| Belgium | Brussels, Bruges, Antwerp |
| Croatia | Dubrovnik, Split, Zagreb |
| Czech Republic | Prague, Brno, Cesky Krumlov |
| Denmark | Copenhagen, Aarhus, Odense |
| Finland | Helsinki, Rovaniemi, Turku |
| France | Paris, Nice, Lyon, Marseille, Bordeaux |
| Germany | Berlin, Munich, Hamburg, Frankfurt, Cologne |
| Greece | Athens, Santorini, Mykonos, Crete |
| Hungary | Budapest, Debrecen, Eger |
| Iceland | Reykjavik, Akureyri, Vik |
| Ireland | Dublin, Galway, Cork |
| Italy | Rome, Florence, Venice, Milan, Naples |
| Netherlands | Amsterdam, Rotterdam, The Hague |
| Norway | Oslo, Bergen, Tromso |
| Poland | Krakow, Warsaw, Gdansk |
| Portugal | Lisbon, Porto, Faro |
| Romania | Bucharest, Brasov, Cluj-Napoca |
| Spain | Barcelona, Madrid, Seville, Valencia, Granada |
| Sweden | Stockholm, Gothenburg, Malmo |
| Switzerland | Zurich, Geneva, Lucerne, Interlaken |
| Turkey | Istanbul, Cappadocia, Antalya |
| United Kingdom | London, Edinburgh, Manchester, Liverpool |

## Installation

The scraper is already included in the Scraparr scrapers directory:
```
/home/peter/work/scraparr/scrapers/tripadvisor_scraper.py
```

## Registration

Register the scraper via Scraparr API:

```bash
curl -X POST http://localhost:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "TripAdvisor Europe",
    "description": "Scrapes attractions, restaurants, and hotels from TripAdvisor for European countries",
    "scraper_type": "web",
    "module_path": "tripadvisor_scraper",
    "class_name": "TripAdvisorScraper",
    "config": {
      "min_delay": 3.0,
      "max_delay": 8.0
    }
  }'
```

Or use the job creation script which auto-registers:
```bash
python scrapers/create_tripadvisor_jobs.py
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `country` | string | "all" | Country slug (e.g., "france") or "all" for all European countries |
| `city` | string | null | Specific city to scrape (overrides country's default cities) |
| `category` | string | "attractions" | Category: "attractions", "restaurants", "hotels", or "all" |
| `max_results` | int | 500 | Maximum results per city/category combination |
| `include_reviews` | bool | false | Whether to fetch reviews for each POI (slower) |
| `max_reviews_per_poi` | int | 10 | Max reviews to fetch if include_reviews is true |
| `min_delay` | float | 3.0 | Minimum delay between requests (seconds) |
| `max_delay` | float | 8.0 | Maximum delay between requests (seconds) |
| `resume` | bool | true | Resume from last progress if interrupted |

## Usage Examples

### 1. Scrape French attractions only
```json
{
  "country": "france",
  "category": "attractions",
  "max_results": 500
}
```

### 2. Scrape all POIs in Paris
```json
{
  "country": "france",
  "city": "Paris",
  "category": "all",
  "max_results": 1000
}
```

### 3. Scrape restaurants in Italy with reviews
```json
{
  "country": "italy",
  "category": "restaurants",
  "max_results": 200,
  "include_reviews": true,
  "max_reviews_per_poi": 5
}
```

### 4. Scrape all European attractions
```json
{
  "country": "all",
  "category": "attractions",
  "max_results": 300,
  "min_delay": 5.0,
  "max_delay": 10.0
}
```

## Database Schema

The scraper creates tables in its assigned schema (e.g., `scraper_5`):

### `pois` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| tripadvisor_id | VARCHAR(50) | TripAdvisor location ID (unique) |
| name | VARCHAR(500) | POI name |
| category | VARCHAR(50) | attraction, restaurant, hotel |
| subcategory | VARCHAR(100) | Specific type (Museum, Italian, etc.) |
| description | TEXT | Full description |
| url | VARCHAR(1000) | TripAdvisor URL |
| rating | FLOAT | 1-5 star rating |
| rating_count | INTEGER | Number of reviews |
| ranking | VARCHAR(200) | Ranking string |
| price_level | VARCHAR(10) | $, $$, $$$, $$$$ |
| price_range | VARCHAR(100) | Price range text |
| address | VARCHAR(500) | Street address |
| city | VARCHAR(255) | City name |
| country | VARCHAR(100) | Country name |
| country_code | VARCHAR(5) | ISO country code |
| latitude | FLOAT | GPS latitude |
| longitude | FLOAT | GPS longitude |
| phone | VARCHAR(50) | Phone number |
| website | VARCHAR(1000) | Official website |
| hours | JSON | Operating hours |
| amenities | JSON | List of features |
| cuisine_types | JSON | Restaurant cuisines |
| hotel_class | VARCHAR(20) | Hotel star rating |
| image_url | VARCHAR(1000) | Primary image |
| images | JSON | Array of image URLs |
| awards | JSON | TripAdvisor awards |
| raw_data | JSON | Complete API response |
| scraped_at | TIMESTAMP | When scraped |
| updated_at | TIMESTAMP | Last update |

### `reviews` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| review_id | VARCHAR(50) | TripAdvisor review ID (unique) |
| poi_id | VARCHAR(50) | Foreign key to pois.tripadvisor_id |
| title | VARCHAR(500) | Review title |
| text | TEXT | Review content |
| rating | INTEGER | 1-5 rating |
| published_date | TIMESTAMP | When published |
| visit_date | VARCHAR(50) | When visited |
| trip_type | VARCHAR(50) | Couples, Family, Solo, Business |
| reviewer_name | VARCHAR(200) | Reviewer display name |
| reviewer_location | VARCHAR(200) | Reviewer location |
| helpful_votes | INTEGER | Helpful vote count |
| owner_response | TEXT | Owner's response |
| raw_data | JSON | Complete review data |
| scraped_at | TIMESTAMP | When scraped |

### `scrape_progress` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| country | VARCHAR(100) | Country being scraped |
| city | VARCHAR(200) | City being scraped |
| category | VARCHAR(50) | Category being scraped |
| offset | INTEGER | Current pagination offset |
| total_found | INTEGER | Total items found |
| completed | INTEGER | 0 = in progress, 1 = done |
| processed_at | TIMESTAMP | Last update time |

## Scheduled Jobs

Use the job creation script to set up weekly schedules:

```bash
# Create attraction-only jobs (default)
python scrapers/create_tripadvisor_jobs.py

# Create jobs for multiple categories
python scrapers/create_tripadvisor_jobs.py --categories attractions restaurants

# List existing jobs
python scrapers/create_tripadvisor_jobs.py --list

# Delete all TripAdvisor jobs
python scrapers/create_tripadvisor_jobs.py --delete-all
```

### Default Schedule

Jobs are spread across the week to avoid overloading:

| Day | Countries |
|-----|-----------|
| Monday | France, Belgium, Netherlands, UK |
| Tuesday | Spain, Italy, Portugal, Greece |
| Wednesday | Germany, Austria, Switzerland, Czech Republic |
| Thursday | Sweden, Norway, Denmark, Finland |
| Friday | Poland, Hungary, Romania, Croatia |
| Saturday | Ireland, Turkey, Iceland |

Each country runs at a different hour (1-4 AM UTC) to spread the load.

## Rate Limiting

TripAdvisor has aggressive bot detection. The scraper uses:

1. **Random delays** between requests (default 3-8 seconds)
2. **Extended delays** every 10 requests
3. **Browser-like headers** to mimic real traffic
4. **Session initialization** by visiting the homepage first

**Recommended settings for production:**
- `min_delay`: 3.0 seconds (minimum)
- `max_delay`: 8.0 seconds (for normal operation)
- Increase delays if you encounter blocks

## Troubleshooting

### "403 Forbidden" errors
- TripAdvisor is blocking requests
- Increase `min_delay` and `max_delay`
- Wait a few hours before retrying
- Consider using rotating proxies

### No data extracted
- TripAdvisor may have changed their page structure
- Check the HTML extraction patterns in `_extract_pois_from_html()`
- Review logs for specific error messages

### Rate limiting (429 errors)
- The scraper handles these automatically
- If persistent, increase delay values significantly

### Resume not working
- Check the `scrape_progress` table in the database
- Ensure the schema exists and tables are created

## Data Quality Notes

- **Coverage**: Major cities have the most complete data
- **Freshness**: Data reflects the scrape time, not real-time
- **Completeness**: Not all fields are available for every POI
- **Ratings**: Based on TripAdvisor's aggregated scores

## Legal Considerations

Web scraping TripAdvisor may be subject to their Terms of Service. This scraper is intended for:
- Personal research and analysis
- Academic projects
- Internal business intelligence

Please review TripAdvisor's terms before using in production.

## Contributing

To improve the scraper:
1. Test changes locally with small datasets
2. Update extraction patterns if TripAdvisor changes their site
3. Add new countries/cities to the `EUROPEAN_COUNTRIES` dictionary
4. Submit improvements via pull request

## Files

- `tripadvisor_scraper.py` - Main scraper implementation
- `create_tripadvisor_jobs.py` - Job scheduling script
- `TRIPADVISOR_README.md` - This documentation

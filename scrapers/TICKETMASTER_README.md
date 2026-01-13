# Ticketmaster Scraper Documentation

## Overview

The Ticketmaster scraper uses the **Ticketmaster Discovery API v2** to collect event data across European countries. The Discovery API is Ticketmaster's official public API for event discovery.

**Key Features:**
- Official API access (no web scraping required)
- Comprehensive event data with venue, pricing, and classification
- Support for 24 European countries
- Rate limiting and pagination handling
- Automatic deduplication

## Getting Started

### 1. Get an API Key

1. Visit https://developer.ticketmaster.com/
2. Click "Get Your API Key" or "Register"
3. Create a free account
4. Navigate to "My Apps" → "Create App"
5. Copy your **Consumer Key** (this is your API key)

**Rate Limits (Free Tier):**
- 5,000 API calls per day
- 5 requests per second

### 2. Register Scraper in Scraparr

```bash
curl -X POST http://scraparr:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Ticketmaster Events",
    "description": "Ticketmaster Discovery API scraper for European events",
    "module_path": "ticketmaster_scraper",
    "class_name": "TicketmasterScraper",
    "config": {
      "api_key": "YOUR_API_KEY_HERE"
    }
  }'
```

## Usage Examples

### Example 1: Scrape UK Events

```json
{
  "api_key": "your_api_key_here",
  "country_code": "GB",
  "max_events": 5000,
  "size": 200
}
```

### Example 2: Scrape London Music Events

```json
{
  "api_key": "your_api_key_here",
  "country_code": "GB",
  "city": "London",
  "segment_name": "Music",
  "max_events": 2000
}
```

### Example 3: Scrape All European Countries

```json
{
  "api_key": "your_api_key_here",
  "country_code": "all",
  "max_events": 1000,
  "min_delay": 0.5,
  "max_delay": 2.0
}
```

### Example 4: Scrape Upcoming Football Events

```json
{
  "api_key": "your_api_key_here",
  "country_code": "DE",
  "keyword": "football",
  "segment_name": "Sports",
  "start_date": "2025-12-01T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z"
}
```

### Example 5: Scrape Rock Concerts in Spain

```json
{
  "api_key": "your_api_key_here",
  "country_code": "ES",
  "keyword": "rock",
  "segment_name": "Music",
  "max_events": 500
}
```

## Parameters Reference

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | string | ✅ Yes | - | Ticketmaster API key |
| `country_code` | string | No | "GB" | ISO country code (e.g., "GB", "DE", "FR") or "all" for all European countries |
| `city` | string | No | - | Filter by city name (e.g., "London", "Berlin") |
| `keyword` | string | No | - | Search keyword (e.g., "rock", "jazz", "football") |
| `genre_id` | string | No | - | Ticketmaster genre ID |
| `segment_name` | string | No | - | Event segment: "Music", "Sports", "Arts & Theatre", "Film", "Miscellaneous" |
| `start_date` | string | No | - | Start date (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ) |
| `end_date` | string | No | - | End date (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ) |
| `size` | int | No | 200 | Events per page (max: 200) |
| `max_events` | int | No | 5000 | Maximum total events to scrape |
| `min_delay` | float | No | 0.5 | Minimum delay between requests (seconds) |
| `max_delay` | float | No | 2.0 | Maximum delay between requests (seconds) |

## Supported Countries

The scraper supports 24 European countries with Ticketmaster presence:

| Country | Code | Country | Code |
|---------|------|---------|------|
| Austria | AT | Italy | IT |
| Belgium | BE | Netherlands | NL |
| Bulgaria | BG | Norway | NO |
| Croatia | HR | Poland | PL |
| Czech Republic | CZ | Portugal | PT |
| Denmark | DK | Romania | RO |
| Finland | FI | Spain | ES |
| France | FR | Sweden | SE |
| Germany | DE | Switzerland | CH |
| Greece | GR | Turkey | TR |
| Hungary | HU | United Kingdom | GB |
| Iceland | IS | | |
| Ireland | IE | | |

## Database Schema

The scraper creates a schema (e.g., `scraper_4`) with an `events` table:

### Events Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key (auto-increment) |
| `event_id` | VARCHAR(100) | Ticketmaster event ID (unique) |
| `name` | VARCHAR(500) | Event name |
| `description` | TEXT | Event description (usually null in list view) |
| `url` | VARCHAR(1000) | Event URL on Ticketmaster |
| `info` | TEXT | Additional info/notes |
| `start_date` | DATETIME | Event start datetime (UTC) |
| `start_date_local` | VARCHAR(100) | Local date/time as string |
| `timezone` | VARCHAR(100) | Timezone of event |
| `status_code` | VARCHAR(50) | Event status (onsale, offsale, cancelled, etc.) |
| `venue_id` | VARCHAR(100) | Venue ID |
| `venue_name` | VARCHAR(500) | Venue name |
| `venue_address` | VARCHAR(500) | Venue address |
| `city` | VARCHAR(255) | City name |
| `postal_code` | VARCHAR(20) | Postal/ZIP code |
| `country` | VARCHAR(100) | Country name |
| `country_code` | VARCHAR(5) | ISO country code |
| `latitude` | FLOAT | Venue latitude |
| `longitude` | FLOAT | Venue longitude |
| `price_min` | FLOAT | Minimum ticket price |
| `price_max` | FLOAT | Maximum ticket price |
| `currency` | VARCHAR(10) | Currency code (EUR, GBP, etc.) |
| `genre` | VARCHAR(255) | Primary genre |
| `segment` | VARCHAR(100) | Event segment (Music, Sports, etc.) |
| `classifications` | TEXT | Full classifications as JSON |
| `promoter_id` | VARCHAR(100) | Promoter ID |
| `promoter_name` | VARCHAR(500) | Promoter name |
| `image_url` | VARCHAR(1000) | Event image URL |
| `image_ratio` | VARCHAR(20) | Image aspect ratio (16_9, 3_2, etc.) |
| `external_links` | TEXT | Social media links as JSON |
| `scraped_at` | DATETIME | When the event was scraped |
| `updated_at` | DATETIME | Last update time |

## Discovery API Details

### Endpoints Used

**Events Search:**
```
GET https://app.ticketmaster.com/discovery/v2/events.json
```

### Common Query Parameters

- `apikey` - Your API key (required)
- `countryCode` - ISO 3166-1 alpha-2 country code
- `city` - City name
- `keyword` - Search keyword
- `segmentName` - Segment filter
- `genreId` - Genre ID
- `startDateTime` - Start date/time (ISO 8601)
- `endDateTime` - End date/time (ISO 8601)
- `size` - Results per page (max 200)
- `page` - Page number
- `sort` - Sort order (date,asc or date,desc)

### Segment IDs

Use these for the `segment_name` parameter:

- **Music** - Concerts, festivals, tours
- **Sports** - Football, basketball, tennis, etc.
- **Arts & Theatre** - Theater, ballet, opera
- **Film** - Cinema, film festivals
- **Miscellaneous** - Other events

### Common Genre IDs

Ticketmaster has hundreds of genres. Some popular ones:

**Music:**
- Rock (KnvZfZ7vAeA)
- Pop (KnvZfZ7vAev)
- Jazz (KnvZfZ7vAvd)
- Classical (KnvZfZ7vAeJ)
- Electronic (KnvZfZ7vAvF)
- Hip-Hop/Rap (KnvZfZ7vAv1)
- Country (KnvZfZ7vAv6)
- Metal (KnvZfZ7vAvt)

**Sports:**
- Football (KnvZfZ7vAdE)
- Basketball (KnvZfZ7vAdJ)
- Tennis (KnvZfZ7vAdD)
- Ice Hockey (KnvZfZ7vAdF)

To find genre IDs, use the Classifications API:
```
GET https://app.ticketmaster.com/discovery/v2/classifications/genres.json?apikey=YOUR_KEY
```

## Rate Limiting Strategy

The scraper implements respectful rate limiting:

**Default delays:**
- Minimum: 0.5 seconds
- Maximum: 2.0 seconds
- Random delay between requests

**API rate limits (free tier):**
- 5,000 calls per day
- 5 requests per second

**Handling 429 (Rate Limit) errors:**
- Automatic 60-second wait
- Retry request

**Calculation:**
- 200 events per page
- ~2 requests per second (safe margin)
- Can scrape ~5,000 events in ~15 minutes

## Weekly Scraping Schedule

### Recommended Schedule for European Countries

Spread scraping across the week to avoid API limits:

**Monday:**
- UK (1am)
- Ireland (2am)
- Germany (3am)
- France (4am)

**Tuesday:**
- Spain (1am)
- Italy (2am)
- Netherlands (3am)
- Belgium (4am)

**Wednesday:**
- Switzerland (1am)
- Austria (2am)
- Sweden (3am)
- Norway (4am)

**Thursday:**
- Denmark (1am)
- Finland (2am)
- Poland (3am)
- Czech Republic (4am)

**Friday:**
- Portugal (1am)
- Greece (2am)
- Hungary (3am)
- Romania (4am)

**Saturday:**
- Croatia (1am)
- Bulgaria (2am)
- Turkey (3am)

### Creating Weekly Jobs

```bash
# UK - Monday 1am
curl -X POST http://scraparr:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Ticketmaster - UK Weekly",
    "description": "Weekly scrape of UK events - Monday at 1:00 AM",
    "params": {
      "api_key": "YOUR_API_KEY",
      "country_code": "GB",
      "max_events": 5000,
      "size": 200
    },
    "schedule_type": "cron",
    "schedule_config": {
      "expression": "0 1 * * 1"
    }
  }'

# Germany - Monday 3am
curl -X POST http://scraparr:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Ticketmaster - Germany Weekly",
    "description": "Weekly scrape of Germany events - Monday at 3:00 AM",
    "params": {
      "api_key": "YOUR_API_KEY",
      "country_code": "DE",
      "max_events": 5000,
      "size": 200
    },
    "schedule_type": "cron",
    "schedule_config": {
      "expression": "0 3 * * 1"
    }
  }'
```

## Query Examples

### Get all events in database

```sql
SELECT * FROM scraper_4.events
ORDER BY start_date DESC
LIMIT 100;
```

### Events by country

```sql
SELECT country, COUNT(*) as event_count
FROM scraper_4.events
GROUP BY country
ORDER BY event_count DESC;
```

### Upcoming music events in London

```sql
SELECT name, start_date_local, venue_name, genre, url
FROM scraper_4.events
WHERE city = 'London'
  AND segment = 'Music'
  AND start_date > NOW()
ORDER BY start_date ASC
LIMIT 20;
```

### Events by genre

```sql
SELECT genre, segment, COUNT(*) as event_count
FROM scraper_4.events
GROUP BY genre, segment
ORDER BY event_count DESC
LIMIT 20;
```

### Events with pricing

```sql
SELECT name, venue_name, city, price_min, price_max, currency
FROM scraper_4.events
WHERE price_min IS NOT NULL
ORDER BY start_date ASC
LIMIT 50;
```

## Testing the Scraper

### Run standalone test

```bash
cd /home/peter/work/scraparr/scrapers

# Set API key
export TICKETMASTER_API_KEY="your_api_key_here"

# Run test
python ticketmaster_scraper.py
```

### Create test job in Scraparr

```bash
# Register scraper (if not already registered)
curl -X POST http://scraparr:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Ticketmaster Events",
    "module_path": "ticketmaster_scraper",
    "class_name": "TicketmasterScraper"
  }'

# Run immediately (replace scraper_id with actual ID)
curl -X POST http://scraparr:8000/api/scrapers/4/run \
  -H 'Content-Type: application/json' \
  -d '{
    "api_key": "your_api_key_here",
    "country_code": "GB",
    "max_events": 100,
    "size": 50
  }'
```

## Troubleshooting

### Error: "api_key is required"

**Solution:** Make sure you include the `api_key` parameter in your scrape params.

```json
{
  "api_key": "your_actual_api_key_here"
}
```

### Error: 401 Unauthorized

**Cause:** Invalid API key

**Solution:**
1. Check your API key is correct
2. Verify your app is activated at https://developer.ticketmaster.com/
3. Try regenerating your API key

### Error: 429 Too Many Requests

**Cause:** Rate limit exceeded

**Solution:**
- Wait for rate limit to reset (daily limit resets at midnight UTC)
- Increase delays: `min_delay: 1.0, max_delay: 3.0`
- Reduce `max_events` per job
- Spread jobs across more hours/days

### No events found

**Possible causes:**
1. No events in that country/city for the date range
2. Invalid city name (try without city filter first)
3. Too restrictive filters (genre + keyword + date range)

**Debug:**
- Try with just `country_code` parameter
- Check Ticketmaster website to see if events exist
- View scraper logs in Scraparr UI

### API Returns Limited Results

**Cause:** Ticketmaster API pagination limit (typically 1000 pages = 200,000 events max)

**Solution:**
- Add date ranges to split queries
- Filter by city for dense areas
- Use segment/genre filters

## Best Practices

### 1. Respect Rate Limits

- Use default delays (0.5-2 seconds)
- Don't scrape same country multiple times per day
- Monitor your daily API usage

### 2. Efficient Querying

- Use specific filters (city, segment, genre) when possible
- Add date ranges for large countries
- Set reasonable `max_events` limits

### 3. Data Quality

- Events are deduped by `event_id`
- Upsert strategy updates existing events
- Scrape weekly to keep data fresh

### 4. Storage Management

- Each country typically has 1,000-10,000 events
- Estimate: ~500 KB per 1,000 events
- All EU countries: ~100,000 events = ~50 MB

## API Documentation

**Official Documentation:**
https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/

**Key Resources:**
- Event Search: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/#search-events-v2
- Classifications: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/#classifications
- Genre List: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/#genre-list

## Support

For issues with:
- **Scraper implementation**: Check scraper logs in Scraparr UI
- **API errors**: Check Ticketmaster API documentation
- **Rate limits**: Contact Ticketmaster for higher limits

## Related Scrapers

- **Eventbrite** (`eventbrite_scraper.py`) - Web scraping, no API
- **UiT in Vlaanderen** (`uitinvlaanderen_scraper.py`) - GraphQL API, Belgian events
- **Park4Night** (`park4night_scraper.py`) - Grid-based scraping, camping spots

---

**Last Updated:** 2025-11-21
**Scraper Version:** 1.0.0
**API Version:** Discovery API v2

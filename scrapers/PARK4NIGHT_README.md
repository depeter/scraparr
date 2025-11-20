# Park4Night Scraper

API scraper for [Park4Night](https://park4night.com) - a platform for finding camping spots, parking locations, and rest areas for motorhomes, campers, and RVs.

## Overview

This scraper provides three specialized classes for interacting with the Park4Night public API:

1. **Park4NightScraper** - Main scraper for location-based searches
2. **Park4NightUserScraper** - User-specific data (places created/reviewed/visited)
3. **Park4NightBulkScraper** - Multi-location bulk data collection

**All scrapers automatically store scraped data in PostgreSQL** with dedicated schemas for isolation and easy querying.

## API Information

- **Base URL**: `https://guest.park4night.com/services/V4.1`
- **Authentication**: None required (public API)
- **Rate Limiting**: Built-in delays to be respectful to the service
- **Documentation**: https://github.com/gtoselli/park4night-api
- **Database Storage**: Automatic PostgreSQL storage with dedicated schemas

## Database Schema

Each scraper instance gets its own PostgreSQL schema (e.g., `scraper_1`) with two tables:

- **`places`** - Camping spots and parking locations with GPS coordinates, ratings, descriptions
- **`reviews`** - User reviews for each place (when `include_reviews: true`)

**Key Features:**
- **Automatic upsert**: Places are updated if they exist, inserted if new
- **No duplicates**: Reviews are deduplicated automatically
- **JSON storage**: Complete API responses stored for reference
- **Timestamps**: Track when data was scraped and updated

For detailed schema documentation, see [PARK4NIGHT_DATABASE_SCHEMA.md](PARK4NIGHT_DATABASE_SCHEMA.md).

## Scraper Classes

### 1. Park4NightScraper

Main scraper for fetching camping spots and parking locations near GPS coordinates.

#### Configuration

**Module Path**: `scrapers.park4night_scraper`
**Class Name**: `Park4NightScraper`
**Type**: API Scraper

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `latitude` | float | Yes | - | GPS latitude coordinate |
| `longitude` | float | Yes | - | GPS longitude coordinate |
| `include_reviews` | boolean | No | `false` | Fetch reviews for each place |
| `max_places` | integer | No | `null` | Limit number of places returned |

#### Example Parameters

```json
{
  "latitude": 48.8566,
  "longitude": 2.3522,
  "include_reviews": false,
  "max_places": 50
}
```

#### Response Data

Returns up to 200 places near the specified coordinates. Each place object includes:

- `id` - Unique place identifier
- `nom` - Place name
- `type` - Type of location
- `latitude` - GPS latitude
- `longitude` - GPS longitude
- `prix` - Price information
- `rating` - User rating
- `nbComment` - Number of comments
- And many more fields...

When `include_reviews: true`:
- `reviews` - Array of review objects
- `review_count` - Number of reviews

#### Use Cases

- **Find nearby camping spots**: Search for places near your current location
- **Plan road trips**: Find places along your route
- **Collect location data**: Build a database of camping spots in a region

#### Example Configurations

**Search near Paris (without reviews)**
```json
{
  "latitude": 48.8566,
  "longitude": 2.3522,
  "max_places": 100
}
```

**Search in Corsica (with reviews)**
```json
{
  "latitude": 42.3383,
  "longitude": 9.5367,
  "include_reviews": true,
  "max_places": 50
}
```

---

### 2. Park4NightUserScraper

Fetch places associated with a specific user.

#### Configuration

**Module Path**: `scrapers.park4night_scraper`
**Class Name**: `Park4NightUserScraper`
**Type**: API Scraper

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mode` | string | Yes | `created` | Type of data: `created`, `reviewed`, or `visited` |
| `uuid` | string | Conditional | - | Username (required for `created` mode) |
| `user_id` | integer | Conditional | - | User ID (required for `reviewed` and `visited` modes) |

#### Example Parameters

**Places created by user**
```json
{
  "mode": "created",
  "uuid": "john_doe"
}
```

**Places reviewed by user**
```json
{
  "mode": "reviewed",
  "user_id": 372940
}
```

**Places visited by user**
```json
{
  "mode": "visited",
  "user_id": 372940
}
```

#### Use Cases

- **User analytics**: Track what places a user has created or reviewed
- **Content curation**: Find all locations added by power users
- **User profiling**: Understand user travel patterns

---

### 3. Park4NightBulkScraper

Fetch data from multiple locations with automatic deduplication.

#### Configuration

**Module Path**: `scrapers.park4night_scraper`
**Class Name**: `Park4NightBulkScraper`
**Type**: API Scraper

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `locations` | array | Yes | - | List of coordinate objects |
| `include_reviews` | boolean | No | `false` | Fetch reviews for all places |
| `delay_seconds` | float | No | `1.0` | Delay between location requests |

#### Example Parameters

**Multi-location search in France**
```json
{
  "locations": [
    {"latitude": 48.8566, "longitude": 2.3522},
    {"latitude": 43.2965, "longitude": 5.3698},
    {"latitude": 45.7640, "longitude": 4.8357},
    {"latitude": 43.6047, "longitude": 1.4442}
  ],
  "include_reviews": false,
  "delay_seconds": 1.0
}
```

**Search with reviews (slower)**
```json
{
  "locations": [
    {"latitude": 50.8503, "longitude": 4.3517},
    {"latitude": 52.3676, "longitude": 4.9041}
  ],
  "include_reviews": true,
  "delay_seconds": 2.0
}
```

#### Features

- **Automatic deduplication**: Places appearing in multiple searches are only included once
- **Rate limiting**: Configurable delays between requests
- **Progress logging**: Detailed logs for monitoring progress
- **Error resilience**: Continues even if individual location requests fail

#### Use Cases

- **Regional data collection**: Gather all places in a specific region
- **Route planning**: Find places along a route with multiple waypoints
- **Comprehensive databases**: Build complete datasets for analysis

---

## Setting Up in Scraparr

### Step 1: Create Scraper

1. Go to the **Scrapers** page
2. Click **"Add Scraper"**
3. Fill in the details:
   - **Name**: `Park4Night Location Search` (or any name)
   - **Description**: `Fetch camping spots near GPS coordinates`
   - **Module Path**: `scrapers.park4night_scraper`
   - **Class Name**: `Park4NightScraper` (or `Park4NightUserScraper` or `Park4NightBulkScraper`)
   - **Type**: API
   - **Configuration**: (optional, leave empty for basic usage)

4. Click **"Validate"** to ensure the scraper loads correctly
5. Click **"Save"**

### Step 2: Create Job

1. Go to the **Jobs** page
2. Click **"Add Job"**
3. Select your Park4Night scraper
4. Set job parameters (see examples above)
5. Optionally configure a schedule:
   - Daily: `0 2 * * *` (runs at 2 AM daily)
   - Weekly: `0 0 * * 0` (runs at midnight every Sunday)
   - Hourly: `0 * * * *` (runs every hour)

### Step 3: Run Job

- Click **"Run Now"** to execute immediately
- Or wait for the scheduled time
- Monitor execution in the **Executions** page

### Step 4: Query Your Data

After the scraper runs, your data is automatically stored in PostgreSQL.

**Connect to database:**
```bash
# Using docker-compose
docker exec -it scraparr-db psql -U scraparr -d scraparr
```

**Example queries:**
```sql
-- List all schemas (one per scraper)
\dn

-- View your scraped places
SELECT id, nom, type, latitude, longitude, rating, ville, pays
FROM scraper_1.places
ORDER BY rating DESC
LIMIT 10;

-- Find free camping spots
SELECT nom, ville, latitude, longitude, rating
FROM scraper_1.places
WHERE prix ILIKE '%gratuit%'
  AND rating >= 4.0
ORDER BY rating DESC;

-- View reviews for a place
SELECT username, note, comment, date
FROM scraper_1.reviews
WHERE place_id = 303989;
```

See [PARK4NIGHT_DATABASE_SCHEMA.md](PARK4NIGHT_DATABASE_SCHEMA.md) for comprehensive query examples.

---

## Example Use Cases

### Use Case 1: Find Camping Spots Near Your Location

**Scenario**: You're traveling through France and want to find camping spots near Paris.

**Setup**:
- Scraper: `Park4NightScraper`
- Parameters:
  ```json
  {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "max_places": 100
  }
  ```

**Result**: Up to 100 camping spots near Paris with details like name, type, price, rating, etc.

---

### Use Case 2: Build a Regional Database

**Scenario**: Collect all camping spots in multiple French cities for a travel app.

**Setup**:
- Scraper: `Park4NightBulkScraper`
- Parameters:
  ```json
  {
    "locations": [
      {"latitude": 48.8566, "longitude": 2.3522},
      {"latitude": 43.2965, "longitude": 5.3698},
      {"latitude": 45.7640, "longitude": 4.8357},
      {"latitude": 43.6047, "longitude": 1.4442},
      {"latitude": 47.2184, "longitude": -1.5536}
    ],
    "include_reviews": true,
    "delay_seconds": 2.0
  }
  ```
- Schedule: Daily at 2 AM (`0 2 * * *`)

**Result**: Comprehensive database of unique camping spots with reviews, updated daily.

---

### Use Case 3: Track Popular Contributors

**Scenario**: Find all places added by a prolific Park4Night contributor.

**Setup**:
- Scraper: `Park4NightUserScraper`
- Parameters:
  ```json
  {
    "mode": "created",
    "uuid": "experienced_camper"
  }
  ```

**Result**: All places created by that user.

---

## Rate Limiting & Best Practices

### Built-in Rate Limiting

All scrapers include rate limiting to be respectful to the Park4Night API:

- **Park4NightScraper**: 0.5s delay when fetching reviews
- **Park4NightUserScraper**: No delays (single request)
- **Park4NightBulkScraper**: Configurable delay (default 1.0s) between locations

### Best Practices

1. **Don't abuse the API**: The Park4Night API is public but not officially supported for scraping
2. **Use reasonable delays**: Keep `delay_seconds` >= 1.0 for bulk operations
3. **Limit results when testing**: Use `max_places` during development
4. **Batch reviews sparingly**: Fetching reviews is slow; only use when necessary
5. **Schedule during off-peak hours**: Run large jobs at night (e.g., 2-4 AM)
6. **Monitor execution logs**: Check for errors or API changes

---

## Data Structure Examples

### Place Object (typical fields)

```json
{
  "id": 303989,
  "nom": "Parking de la plage",
  "type": "Parking",
  "latitude": 42.3383,
  "longitude": 9.5367,
  "prix": "Gratuit",
  "rating": 4.2,
  "nbComment": 15,
  "pays": "France",
  "ville": "Ajaccio",
  "description": "Parking proche de la plage avec vue sur la mer",
  "services": ["WC", "Eau"],
  "photos": [...]
}
```

### Review Object (when `include_reviews: true`)

```json
{
  "id": 123456,
  "lieu_id": 303989,
  "user_id": 789,
  "username": "traveler123",
  "note": 5,
  "comment": "Excellent spot, very peaceful",
  "date": "2024-08-15",
  "photos": [...]
}
```

---

## Troubleshooting

### "latitude and longitude parameters are required"

Make sure you're passing both parameters:
```json
{
  "latitude": 48.8566,
  "longitude": 2.3522
}
```

### "uuid parameter is required for mode='created'"

For user scrapers in `created` mode, you need the username (uuid):
```json
{
  "mode": "created",
  "uuid": "username_here"
}
```

### "locations parameter is required"

For bulk scrapers, provide an array of location objects:
```json
{
  "locations": [
    {"latitude": 48.8566, "longitude": 2.3522}
  ]
}
```

### API returns empty results

- Check that your coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)
- Try different coordinates - some areas may have no registered places
- Check execution logs for API errors

### Scraper times out

- Reduce `max_places` parameter
- Increase job timeout in Scraparr settings
- For bulk scraper, reduce number of locations or increase `delay_seconds`

---

## API Endpoints Used

| Endpoint | Purpose | Parameters |
|----------|---------|------------|
| `lieuxGetFilter.php` | Get places by coordinates | `latitude`, `longitude` |
| `commGet.php` | Get reviews for a place | `lieu_id` |
| `lieuGetUser.php` | Get places created by user | `uuid` |
| `lieuGetCommUser.php` | Get places reviewed/visited | `user_id` |

---

## Future Enhancements

Potential improvements for future versions:

- [ ] Support for filtering by place type (parking, camping, etc.)
- [ ] Support for price filtering
- [ ] Support for rating filtering
- [ ] Incremental updates (only fetch new places since last run)
- [ ] Export to GPX format for GPS devices
- [ ] Custom database tables for better data organization
- [ ] Photo downloading support
- [ ] Multi-language support for place descriptions

---

## Support

For issues or questions:

1. Check the execution logs in Scraparr
2. Review this documentation
3. Consult the [Park4Night API docs](https://github.com/gtoselli/park4night-api)
4. Check Scraparr's general scraper documentation

---

## License

This scraper is provided as-is for use with Scraparr. The Park4Night API is used according to their public endpoint availability. Always respect their terms of service.

# Park4Night Database Schema

This document describes the PostgreSQL database schema automatically created for Park4Night scrapers.

## Overview

When you create a Park4Night scraper in Scraparr, the system automatically:

1. Creates a dedicated PostgreSQL schema (e.g., `scraper_1`, `scraper_2`)
2. Creates tables within that schema to store scraped data
3. Automatically inserts/updates data after each scrape

## Schema Isolation

Each Park4Night scraper instance gets its own PostgreSQL schema, allowing you to:
- Run multiple scraper instances independently
- Keep data from different regions/sources separate
- Drop/recreate individual scraper data without affecting others

**Example schema names:**
```
scraper_1  (First Park4Night scraper)
scraper_2  (Second Park4Night scraper)
scraper_3  (Third Park4Night scraper)
```

## Tables

### Table: `places`

Stores camping spots, parking locations, and rest areas.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique place ID from Park4Night API |
| `nom` | VARCHAR(500) | | Place name |
| `type` | VARCHAR(100) | | Type of location (Parking, Camping, etc.) |
| `latitude` | FLOAT | | GPS latitude |
| `longitude` | FLOAT | | GPS longitude |
| `pays` | VARCHAR(100) | | Country |
| `ville` | VARCHAR(200) | | City/town |
| `description` | TEXT | | Place description |
| `prix` | VARCHAR(100) | | Price information |
| `rating` | FLOAT | | Average user rating |
| `nb_comment` | INTEGER | | Number of comments/reviews |
| `services` | JSON | | Available services (array) |
| `raw_data` | JSON | | Complete API response |
| `scraped_at` | TIMESTAMP | DEFAULT now() | First scrape timestamp |
| `updated_at` | TIMESTAMP | DEFAULT now() | Last update timestamp |

**Primary Key:** `id`

**Upsert Behavior:**
- If a place with the same `id` exists, it will be **updated** with new data
- If it's a new place, it will be **inserted**
- This ensures you always have the latest information

**Indexes:** Automatic index on `id` (primary key)

---

### Table: `reviews`

Stores user reviews for places. Only created for scrapers that fetch review data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-incrementing review ID |
| `place_id` | INTEGER | INDEX | Foreign key to places.id |
| `review_id` | INTEGER | | Original review ID from API |
| `user_id` | INTEGER | | Reviewer's user ID |
| `username` | VARCHAR(200) | | Reviewer's username |
| `note` | FLOAT | | Rating given by reviewer |
| `comment` | TEXT | | Review text |
| `date` | VARCHAR(50) | | Review date |
| `raw_data` | JSON | | Complete review data from API |
| `scraped_at` | TIMESTAMP | DEFAULT now() | When review was scraped |

**Primary Key:** `id` (auto-increment)

**Indexes:**
- `place_id` (for efficient lookups)
- Primary key on `id`

**Insert Behavior:**
- Reviews are inserted only if they don't already exist
- Duplicates are silently skipped (`ON CONFLICT DO NOTHING`)

---

## Schema Creation

### Automatic Creation

The schema and tables are created automatically when:
1. You create a Park4Night scraper via the Scraparr UI/API
2. The scraper runs for the first time

No manual setup is required.

### Manual Schema Inspection

To inspect the schema manually:

```sql
-- Connect to PostgreSQL
psql -U scraparr -d scraparr

-- List all schemas
\dn

-- List tables in a specific schema
\dt scraper_1.*

-- Describe table structure
\d scraper_1.places
\d scraper_1.reviews

-- View data
SELECT * FROM scraper_1.places LIMIT 10;
SELECT * FROM scraper_1.reviews WHERE place_id = 303989;
```

---

## Querying Data

### Basic Queries

**Get all places:**
```sql
SELECT id, nom, type, latitude, longitude, pays, ville, rating
FROM scraper_1.places
ORDER BY scraped_at DESC;
```

**Find places by location:**
```sql
SELECT nom, type, latitude, longitude, rating
FROM scraper_1.places
WHERE pays = 'France'
  AND ville = 'Paris'
ORDER BY rating DESC;
```

**Find free parking spots:**
```sql
SELECT nom, ville, latitude, longitude
FROM scraper_1.places
WHERE prix ILIKE '%gratuit%' OR prix ILIKE '%free%'
ORDER BY rating DESC;
```

**Get places with good ratings:**
```sql
SELECT nom, type, rating, nb_comment
FROM scraper_1.places
WHERE rating >= 4.0
  AND nb_comment >= 5
ORDER BY rating DESC, nb_comment DESC;
```

**Search by GPS proximity (approximate):**
```sql
SELECT nom, type, latitude, longitude,
       SQRT(POW(latitude - 48.8566, 2) + POW(longitude - 2.3522, 2)) AS distance
FROM scraper_1.places
ORDER BY distance
LIMIT 20;
```

### Review Queries

**Get reviews for a place:**
```sql
SELECT username, note, comment, date
FROM scraper_1.reviews
WHERE place_id = 303989
ORDER BY date DESC;
```

**Find places with most reviews:**
```sql
SELECT p.nom, p.type, COUNT(r.id) as review_count, AVG(r.note) as avg_rating
FROM scraper_1.places p
LEFT JOIN scraper_1.reviews r ON p.id = r.place_id
GROUP BY p.id, p.nom, p.type
ORDER BY review_count DESC
LIMIT 20;
```

**Find highly-rated reviews:**
```sql
SELECT p.nom, r.username, r.note, r.comment
FROM scraper_1.reviews r
JOIN scraper_1.places p ON r.place_id = p.id
WHERE r.note >= 4.5
ORDER BY r.note DESC, p.rating DESC;
```

### Advanced Queries

**Places by country with stats:**
```sql
SELECT
    pays,
    COUNT(*) as total_places,
    AVG(rating) as avg_rating,
    SUM(nb_comment) as total_reviews
FROM scraper_1.places
WHERE pays IS NOT NULL
GROUP BY pays
ORDER BY total_places DESC;
```

**Recently added places:**
```sql
SELECT nom, type, ville, pays, rating, scraped_at
FROM scraper_1.places
WHERE scraped_at >= NOW() - INTERVAL '7 days'
ORDER BY scraped_at DESC;
```

**Extract services from JSON:**
```sql
SELECT nom, services
FROM scraper_1.places
WHERE services ? 'WC'  -- Has WC service
   OR services ? 'Eau';  -- Has water
```

**Full-text search in descriptions:**
```sql
SELECT nom, description, rating
FROM scraper_1.places
WHERE description ILIKE '%mer%'  -- French for "sea"
   OR description ILIKE '%plage%'  -- French for "beach"
ORDER BY rating DESC;
```

---

## Data Retention & Updates

### Update Strategy

**Places Table:**
- **UPSERT**: Existing places are updated with latest data on each scrape
- **Timestamp**: `updated_at` tracks when a place was last updated
- **History**: No version history; only current state is kept

**Reviews Table:**
- **INSERT ONLY**: Reviews are never updated, only added
- **Deduplication**: Duplicate reviews are skipped
- **No Deletion**: Reviews are kept indefinitely

### Incremental Updates

The scrapers are designed for incremental updates:

```python
# Example: Daily scrape of the same area
# Day 1: Fetches 100 places → all inserted
# Day 2: Fetches 105 places (5 new) → 100 updated, 5 inserted
# Day 3: Fetches 102 places (2 removed from API) → 102 updated
```

Places that disappear from the API are NOT automatically removed from your database.

### Manual Data Management

**Clear all data for a scraper:**
```sql
TRUNCATE scraper_1.places, scraper_1.reviews CASCADE;
```

**Delete old places not updated recently:**
```sql
DELETE FROM scraper_1.places
WHERE updated_at < NOW() - INTERVAL '30 days';
```

**Remove scraper schema entirely:**
```sql
DROP SCHEMA scraper_1 CASCADE;
```
⚠️ **Warning:** This deletes all data permanently!

---

## Performance Optimization

### Indexes

The default schema includes indexes on:
- `places.id` (primary key)
- `reviews.id` (primary key)
- `reviews.place_id` (foreign key lookup)

### Additional Recommended Indexes

For large datasets, consider adding:

```sql
-- Index for location-based searches
CREATE INDEX idx_places_location ON scraper_1.places (latitude, longitude);

-- Index for country/city filtering
CREATE INDEX idx_places_location_text ON scraper_1.places (pays, ville);

-- Index for rating queries
CREATE INDEX idx_places_rating ON scraper_1.places (rating DESC);

-- Full-text search on descriptions
CREATE INDEX idx_places_description_fts ON scraper_1.places
USING gin(to_tsvector('french', description));
```

### Query Optimization

**Use EXPLAIN to analyze queries:**
```sql
EXPLAIN ANALYZE
SELECT * FROM scraper_1.places
WHERE pays = 'France'
  AND rating >= 4.0;
```

---

## Data Export

### Export to CSV

```sql
COPY (
    SELECT id, nom, type, latitude, longitude, pays, ville, rating
    FROM scraper_1.places
    ORDER BY rating DESC
) TO '/tmp/park4night_places.csv' WITH CSV HEADER;
```

### Export to JSON

```sql
COPY (
    SELECT jsonb_build_object(
        'places', jsonb_agg(to_jsonb(places))
    )
    FROM scraper_1.places
) TO '/tmp/park4night_places.json';
```

---

## Schema Migrations

### Adding Custom Columns

If you need additional columns:

```sql
-- Add a custom column
ALTER TABLE scraper_1.places
ADD COLUMN custom_notes TEXT;

-- Add a visited flag
ALTER TABLE scraper_1.places
ADD COLUMN visited BOOLEAN DEFAULT FALSE;

-- Add a favorite flag
ALTER TABLE scraper_1.places
ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE;
```

⚠️ **Note:** Custom columns will NOT be populated by the scraper. You'll need to update them manually.

---

## Troubleshooting

### Schema not created

**Problem:** Tables don't exist after running scraper.

**Solution:**
1. Check scraper execution logs for errors
2. Verify PostgreSQL connection in Scraparr config
3. Ensure the database user has CREATE privileges

### Duplicate key errors

**Problem:** Error inserting data due to duplicate IDs.

**Cause:** Multiple scrapers writing to the same schema.

**Solution:** Each scraper should have its own unique schema name.

### Slow queries

**Problem:** Queries taking too long on large datasets.

**Solution:**
1. Add indexes (see Performance Optimization)
2. Use `LIMIT` for exploratory queries
3. Filter by country/region first
4. Consider partitioning by country for very large datasets

### Missing reviews

**Problem:** Reviews not being stored even with `include_reviews: true`.

**Cause:** The Park4Night scraper only stores reviews when explicitly requested.

**Solution:**
- Ensure `include_reviews: true` in job parameters
- Check execution logs for API errors
- Verify the `reviews` table exists: `\dt scraper_1.reviews`

---

## Example Application: Finding Great Camping Spots

```sql
-- Find top-rated free camping spots near the Mediterranean
WITH mediterranean_area AS (
    SELECT *
    FROM scraper_1.places
    WHERE latitude BETWEEN 41.0 AND 44.0
      AND longitude BETWEEN 3.0 AND 10.0
      AND (prix ILIKE '%gratuit%' OR prix ILIKE '%free%')
)
SELECT
    nom,
    ville,
    pays,
    rating,
    nb_comment,
    latitude,
    longitude,
    description
FROM mediterranean_area
WHERE rating >= 4.0
  AND nb_comment >= 3
ORDER BY rating DESC, nb_comment DESC
LIMIT 20;
```

---

## Security Considerations

1. **Schema Isolation**: Each scraper has its own schema - prevents data mixing
2. **No User Input**: All data comes from Park4Night API - no SQL injection risk
3. **JSON Storage**: Raw API responses stored in JSON columns for audit trail
4. **Timestamps**: Track when data was scraped for data freshness validation

---

## Summary

- ✅ **Automatic Setup**: Schema and tables created automatically
- ✅ **Upsert Logic**: Places updated on each scrape, no duplicates
- ✅ **Review Storage**: Optional review collection with deduplication
- ✅ **JSON Storage**: Complete API responses preserved
- ✅ **Timestamping**: Track scrape time and updates
- ✅ **Queryable**: Standard SQL queries for analysis
- ✅ **Isolated**: Each scraper has its own schema

For more information, see the main [Park4Night Scraper README](PARK4NIGHT_README.md).

# Park4Night Scraper - Quick Start Guide

Get up and running with the Park4Night scraper in 5 minutes.

## 1. Add the Scraper

**Via Scraparr UI:**

1. Navigate to **Scrapers** → **Add Scraper**
2. Fill in:
   - **Name**: `Park4Night France`
   - **Description**: `Camping spots in France`
   - **Module Path**: `scrapers.park4night_scraper`
   - **Class Name**: `Park4NightScraper`
   - **Type**: API
   - **Config**: (leave empty)
3. Click **Validate** → **Save**

## 2. Create a Job

1. Navigate to **Jobs** → **Add Job**
2. Select your `Park4Night France` scraper
3. Set parameters:
   ```json
   {
     "latitude": 48.8566,
     "longitude": 2.3522,
     "max_places": 100
   }
   ```
4. Optional: Set schedule to `0 2 * * *` (daily at 2 AM)
5. Click **Save**

## 3. Run the Job

1. Click **Run Now** on your job
2. Wait for execution to complete (~30 seconds)
3. Check execution logs for success message

## 4. Query the Data

Connect to PostgreSQL:
```bash
docker exec -it scraparr-db psql -U scraparr -d scraparr
```

Find your schema (usually `scraper_1` for the first scraper):
```sql
\dn
```

Query places:
```sql
SELECT nom, type, rating, ville, latitude, longitude
FROM scraper_1.places
ORDER BY rating DESC
LIMIT 20;
```

## Common Configurations

### Search Near Major Cities

**Paris:**
```json
{
  "latitude": 48.8566,
  "longitude": 2.3522,
  "max_places": 100
}
```

**Marseille:**
```json
{
  "latitude": 43.2965,
  "longitude": 5.3698,
  "max_places": 100
}
```

**Lyon:**
```json
{
  "latitude": 45.7640,
  "longitude": 4.8357,
  "max_places": 100
}
```

### Include Reviews (Slower)

```json
{
  "latitude": 48.8566,
  "longitude": 2.3522,
  "max_places": 20,
  "include_reviews": true
}
```

### Bulk Scraper (Multiple Locations)

1. Use **Class Name**: `Park4NightBulkScraper`
2. Parameters:
   ```json
   {
     "locations": [
       {"latitude": 48.8566, "longitude": 2.3522},
       {"latitude": 43.2965, "longitude": 5.3698},
       {"latitude": 45.7640, "longitude": 4.8357}
     ],
     "delay_seconds": 1.0
   }
   ```

## Useful Queries

**Free camping spots:**
```sql
SELECT nom, ville, rating
FROM scraper_1.places
WHERE prix ILIKE '%gratuit%'
ORDER BY rating DESC;
```

**Highly rated spots (4+ stars, 5+ reviews):**
```sql
SELECT nom, ville, rating, nb_comment
FROM scraper_1.places
WHERE rating >= 4.0 AND nb_comment >= 5
ORDER BY rating DESC;
```

**By country:**
```sql
SELECT pays, COUNT(*) as total
FROM scraper_1.places
GROUP BY pays
ORDER BY total DESC;
```

**Recently scraped:**
```sql
SELECT nom, ville, rating, scraped_at
FROM scraper_1.places
WHERE scraped_at >= NOW() - INTERVAL '1 day'
ORDER BY scraped_at DESC;
```

## Schedules

**Daily at 2 AM:**
```
0 2 * * *
```

**Every 6 hours:**
```
0 */6 * * *
```

**Weekly (Sunday midnight):**
```
0 0 * * 0
```

## Troubleshooting

**No results returned:**
- Check coordinates are valid
- Try different coordinates
- Check execution logs for API errors

**Schema not found:**
- Run the scraper at least once
- Check scraper ID in database
- Schema name is `scraper_{id}`

**Slow execution:**
- Reduce `max_places`
- Don't use `include_reviews` for testing
- For bulk scraper, increase `delay_seconds`

## Next Steps

- Read full documentation: [PARK4NIGHT_README.md](PARK4NIGHT_README.md)
- Database schema details: [PARK4NIGHT_DATABASE_SCHEMA.md](PARK4NIGHT_DATABASE_SCHEMA.md)
- Schedule regular updates for your favorite regions
- Export data for use in external applications

## Export Data

**To CSV:**
```sql
COPY (
    SELECT nom, type, latitude, longitude, rating, ville, pays
    FROM scraper_1.places
    ORDER BY rating DESC
) TO '/tmp/park4night.csv' WITH CSV HEADER;
```

**To JSON:**
```bash
# From host machine
docker exec scraparr-db psql -U scraparr -d scraparr -t -c "SELECT jsonb_agg(to_jsonb(p)) FROM scraper_1.places p;" > park4night.json
```

---

That's it! You now have a working Park4Night scraper that automatically stores camping and parking locations in PostgreSQL. Happy camping! 🏕️

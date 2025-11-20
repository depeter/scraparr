# Tripflow ETL Pipeline

This ETL (Extract, Transform, Load) pipeline syncs location data from Scraparr's multiple scrapers into a consolidated Tripflow PostgreSQL database.

## Overview

The ETL pipeline:
1. **Extracts** data from Scraparr's scraper schemas (Park4Night, UiT in Vlaanderen, etc.)
2. **Transforms** the data into Tripflow's unified schema
3. **Loads** it into a dedicated Tripflow PostgreSQL database with PostGIS

## Architecture

```
Scraparr DB                     Tripflow DB
┌─────────────┐                ┌──────────────┐
│ scraper_2   │                │   tripflow   │
│ (Park4Night)│───┐            │              │
└─────────────┘   │            │  locations   │
                  ├── ETL ───▶ │   events     │
┌─────────────┐   │ Pipeline   │   reviews    │
│ scraper_3   │───┘            │  sync_log    │
│ (UiT Events)│                └──────────────┘
└─────────────┘
```

## Quick Start

### 1. Set Up Tripflow Database

Using Docker (recommended):
```bash
cd /home/peter/work/tripflow
docker compose -f docker-compose.tripflow-db.yml up -d

# Verify database is running
docker exec tripflow-postgres psql -U tripflow -d tripflow -c '\dn'
```

Or manually with existing PostgreSQL:
```bash
cd /home/peter/work/tripflow/backend/db
chmod +x setup_tripflow_db.sh
./setup_tripflow_db.sh
```

### 2. Configure ETL

```bash
cd /home/peter/work/scraparr/etl
cp .env.example .env
# Edit .env with your database URLs
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run ETL Manually

```bash
python tripflow_etl.py
```

## Database Schema

### Main Tables

#### `tripflow.locations`
Consolidated location data from all sources:
- Camping spots from Park4Night
- Events venues from UiT in Vlaanderen
- Future: CamperContact, OpenStreetMap POIs

Key fields:
- `id`: Internal ID
- `external_id`: Source system ID
- `source`: Data source (park4night, uitinvlaanderen, etc.)
- `location_type`: CAMPSITE, PARKING, EVENT, etc.
- `geom`: PostGIS geometry point
- `amenities`: JSON array of features
- `popularity_score`: Calculated ranking score

#### `tripflow.events`
Time-based events linked to locations:
- Cultural events from UiT in Vlaanderen
- Future: Festivals, concerts, markets

#### `tripflow.sync_log`
ETL execution history and statistics

#### `tripflow.data_quality_metrics`
Data completeness and quality tracking by source

## ETL Features

### Smart Deduplication
- Identifies potential duplicate locations within 50 meters
- Compares across different data sources
- Logs duplicates for review (doesn't auto-merge)

### Data Quality Scoring
- Calculates completeness score (0-100) for each source
- Tracks missing fields (description, images, address, etc.)
- Generates daily quality metrics

### Popularity Scoring
Automatic calculation based on:
- Rating (0-50 points)
- Number of ratings (0-30 points)
- Number of reviews (0-20 points)
Used for recommendation ranking in Tripflow

### Incremental Updates
- UPSERT logic (INSERT or UPDATE based on external_id)
- Preserves existing data while updating changed fields
- Tracks last update timestamp

## Scheduling with Scraparr

### Register the ETL Scraper

```bash
curl -X POST http://localhost:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Tripflow ETL Sync",
    "description": "Sync all Scraparr data to Tripflow database",
    "module_path": "tripflow_etl_scraper",
    "class_name": "TripflowETLScraper",
    "scraper_type": "api",
    "is_active": true
  }'
```

### Create Scheduled Job

Daily sync at 4 AM:
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Tripflow Daily ETL",
    "description": "Daily sync of all location data to Tripflow",
    "schedule_type": "cron",
    "schedule_config": {
      "expression": "0 4 * * *"
    },
    "params": {
      "sync_type": "full",
      "sources": ["park4night", "uitinvlaanderen"],
      "enable_deduplication": true
    },
    "is_active": true
  }'
```

Hourly incremental sync:
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Tripflow Hourly Sync",
    "schedule_type": "interval",
    "schedule_config": {
      "hours": 1
    },
    "params": {
      "sync_type": "incremental"
    }
  }'
```

## Configuration

### Environment Variables

```env
# Database URLs
SCRAPARR_DB_URL=postgresql://scraparr:scraparr@localhost:5432/scraparr
TRIPFLOW_DB_URL=postgresql://tripflow:tripflow@localhost:5433/tripflow

# ETL Settings
BATCH_SIZE=1000                # Records per batch
ENABLE_DEDUPLICATION=true      # Run dedup check
DEDUP_DISTANCE_METERS=50       # Distance for duplicate detection
```

### ETL Parameters

When running through Scraparr:

```json
{
  "sync_type": "full",           // 'full' or 'incremental'
  "sources": [                   // Which sources to sync
    "park4night",
    "uitinvlaanderen"
  ],
  "enable_deduplication": true   // Run deduplication
}
```

## Monitoring

### Check Sync Status

```sql
-- Connect to Tripflow database
psql -U tripflow -d tripflow

-- Recent sync jobs
SELECT
    source,
    started_at,
    completed_at,
    records_processed,
    records_failed,
    status
FROM tripflow.sync_log
ORDER BY started_at DESC
LIMIT 10;

-- Location counts by source
SELECT
    source,
    COUNT(*) as total,
    AVG(popularity_score) as avg_popularity
FROM tripflow.locations
GROUP BY source;

-- Data quality metrics
SELECT
    source,
    metric_date,
    total_records,
    completeness_score
FROM tripflow.data_quality_metrics
ORDER BY metric_date DESC;
```

### Check for Duplicates

```sql
-- Find potential duplicates
WITH potential_duplicates AS (
    SELECT
        l1.name as name1,
        l2.name as name2,
        l1.source as source1,
        l2.source as source2,
        ST_Distance(l1.geom::geography, l2.geom::geography) as distance_meters
    FROM tripflow.locations l1
    JOIN tripflow.locations l2
        ON l1.id < l2.id
        AND l1.source != l2.source
        AND ST_DWithin(l1.geom::geography, l2.geom::geography, 50)
)
SELECT * FROM potential_duplicates
ORDER BY distance_meters
LIMIT 20;
```

## Troubleshooting

### ETL Fails to Connect

Check database connectivity:
```bash
# Test Scraparr connection
psql postgresql://scraparr:scraparr@localhost:5432/scraparr -c "SELECT 1"

# Test Tripflow connection (note port 5433 if using Docker)
psql postgresql://tripflow:tripflow@localhost:5433/tripflow -c "SELECT 1"
```

### No Data Being Synced

1. Check Scraparr has data:
```sql
-- Connect to Scraparr
psql -U scraparr -d scraparr

-- Check schemas exist
\dn

-- Check for Park4Night data
SELECT COUNT(*) FROM scraper_2.places;

-- Check for UiT events
SELECT COUNT(*) FROM scraper_3.events;
```

2. Check ETL logs:
```bash
# If running through Scraparr
docker logs scraparr-backend --tail 100 | grep -i etl

# If running standalone
python tripflow_etl.py
```

### Performance Issues

For large datasets (>100k records):

1. Increase batch size:
```env
BATCH_SIZE=5000
```

2. Add database indexes (already included in schema):
```sql
-- Verify indexes exist
\di tripflow.*
```

3. Run VACUUM ANALYZE after large imports:
```sql
VACUUM ANALYZE tripflow.locations;
```

## Data Flow Example

### Park4Night → Tripflow

**Source** (Scraparr scraper_2.places):
```json
{
  "id": 12345,
  "nom": "Camping La Plage",
  "type": "Camping",
  "latitude": 43.5,
  "longitude": 3.2,
  "pays": "France",
  "rating": 4.5,
  "services": ["eau", "electricite", "wifi"]
}
```

**Transformed** (Tripflow locations):
```json
{
  "external_id": "park4night_12345",
  "source": "park4night",
  "name": "Camping La Plage",
  "location_type": "CAMPSITE",
  "latitude": 43.5,
  "longitude": 3.2,
  "geom": "POINT(3.2 43.5)",
  "country": "France",
  "rating": 4.5,
  "amenities": ["water", "electricity", "wifi"],
  "popularity_score": 48.5
}
```

### UiT Event → Tripflow

**Source** (Scraparr scraper_3.events):
```json
{
  "event_id": "abc-123",
  "name": "Jazz Festival",
  "location_name": "Concert Hall",
  "city": "Ghent",
  "start_date": "2024-07-01",
  "end_date": "2024-07-03"
}
```

**Transformed** (Tripflow locations + events):
```json
// Location record
{
  "external_id": "uit_location_abc-123",
  "source": "uitinvlaanderen",
  "name": "Concert Hall",
  "location_type": "EVENT",
  "city": "Ghent",
  "country": "Belgium"
}

// Event record
{
  "location_id": 567,
  "external_id": "abc-123",
  "source": "uitinvlaanderen",
  "name": "Jazz Festival",
  "start_date": "2024-07-01",
  "end_date": "2024-07-03"
}
```

## Future Enhancements

### Planned Features
- [ ] Real-time sync via database triggers
- [ ] Automatic duplicate merging with rules
- [ ] Image downloading and caching
- [ ] Review sentiment analysis
- [ ] Weather data integration
- [ ] Opening hours parsing
- [ ] Multi-language support

### Additional Data Sources
- [ ] CamperContact scraper integration
- [ ] OpenStreetMap POI import
- [ ] Google Places enrichment
- [ ] Booking.com hotel data
- [ ] Local event APIs

## Support

For issues or questions:
1. Check ETL logs in `tripflow.sync_log` table
2. Review Scraparr execution logs
3. Verify database connectivity
4. Check this README for common solutions

## License

Part of the Tripflow project - see main project LICENSE
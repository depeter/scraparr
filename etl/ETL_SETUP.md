# Tripflow ETL Setup Guide

## ✅ ETL is Ready to Use!

The ETL pipeline syncs data from Scraparr to Tripflow continuously.

### Current Status on Scraparr Server

**Location:** `/home/peter/scraparr/etl/`

**Data Available:**
- 🏕️ **221,430** Park4Night camping/parking locations
- 🎭 **15,683** UiT in Vlaanderen cultural events
- **Total:** ~237,000 records ready to migrate

**Performance:** ~450 records/second (~8-10 minutes for full sync)

---

## Quick Commands

### Run Full Migration (One-time)

```bash
ssh peter@scraparr
cd /home/peter/scraparr/etl
venv/bin/python tripflow_etl.py
```

**Expected time:** 8-10 minutes
**Result:** All Park4Night places and UiT events migrated to Tripflow

### Check Progress

```bash
# During migration - watch logs
ssh peter@scraparr "cd /home/peter/scraparr/etl && tail -f migration.log"

# After migration - check counts
ssh peter@scraparr "docker exec tripflow-postgres psql -U postgres -d tripflow -c '
SELECT
    source,
    COUNT(*) as total,
    location_type,
    COUNT(DISTINCT country) as countries
FROM tripflow.locations
GROUP BY source, location_type
ORDER BY total DESC;
'"
```

### View Sync History

```bash
ssh peter@scraparr "docker exec tripflow-postgres psql -U postgres -d tripflow -c '
SELECT
    source,
    started_at,
    completed_at,
    records_processed,
    records_inserted,
    records_failed,
    status
FROM tripflow.sync_log
ORDER BY started_at DESC
LIMIT 10;
'"
```

---

## Configuration

**Location:** `/home/peter/scraparr/etl/.env`

```env
# Source database (Scraparr)
SCRAPARR_DB_URL=postgresql://scraparr:scraparr@localhost:5434/scraparr

# Target database (Tripflow)
TRIPFLOW_DB_URL=postgresql://postgres:tripflow@localhost:5433/tripflow

# ETL Settings
BATCH_SIZE=1000                  # Records per batch (higher = faster)
ENABLE_DEDUPLICATION=true        # Find duplicates within 50m
DEDUP_DISTANCE_METERS=50         # Duplicate detection radius
```

---

## Scheduling Options

### Option 1: Cron Job (Recommended for Daily Sync)

```bash
# Edit crontab
crontab -e

# Add daily sync at 4:00 AM
0 4 * * * cd /home/peter/scraparr/etl && venv/bin/python tripflow_etl.py >> /home/peter/scraparr/etl/cron.log 2>&1
```

### Option 2: Systemd Service (For Continuous Monitoring)

Create `/etc/systemd/system/tripflow-etl.service`:

```ini
[Unit]
Description=Tripflow ETL Pipeline
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=peter
WorkingDirectory=/home/peter/scraparr/etl
ExecStart=/home/peter/scraparr/etl/venv/bin/python /home/peter/scraparr/etl/tripflow_etl.py
StandardOutput=append:/home/peter/scraparr/etl/etl.log
StandardError=append:/home/peter/scraparr/etl/etl-error.log

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tripflow-etl.timer
sudo systemctl start tripflow-etl.timer
```

### Option 3: Scraparr Scheduler Integration

Register ETL as a scraper in Scraparr for UI management:

```bash
curl -X POST http://localhost:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Tripflow ETL Sync",
    "description": "Sync Scraparr data to Tripflow database",
    "module_path": "tripflow_etl_scraper",
    "class_name": "TripflowETLScraper",
    "is_active": true
  }'

# Then create a daily job in Scraparr UI
```

---

## Data Flow

```
Scraparr DB (Port 5434)          Tripflow DB (Port 5433)
┌──────────────────────┐         ┌──────────────────────┐
│ scraper_1.places     │         │ tripflow.locations   │
│ (Park4Night)         │────────▶│ (Normalized schema)  │
│ 221,430 records      │   ETL   │                      │
├──────────────────────┤         ├──────────────────────┤
│ scraper_2.events     │         │ tripflow.events      │
│ (UiT Vlaanderen)     │────────▶│ (Linked to location) │
│ 15,683 records       │         │                      │
└──────────────────────┘         └──────────────────────┘
```

### Transformation Examples

**Park4Night → Tripflow Location:**
```
Input:  id=12345, nom="Camping La Plage", type="Camping", pays="France"
Output: external_id="park4night_12345", source="park4night",
        location_type="CAMPSITE", country="France"
```

**UiT Event → Tripflow Event + Location:**
```
Input:  event_id="abc-123", name="Jazz Festival", city="Ghent"
Output: Location record (external_id="uit_location_abc-123")
        Event record (linked to location_id)
```

---

## Monitoring & Troubleshooting

### Check ETL Status

```bash
# Live monitoring
ssh peter@scraparr "cd /home/peter/scraparr/etl && venv/bin/python test_etl.py"

# Expected output:
# ✓ Scraparr: 221,430 Park4Night places
# ✓ Scraparr: 15,683 UiT events
# ✓ Tripflow: X existing locations
# ✓ All connections successful!
```

### Common Issues

**Connection errors:**
- Check Docker containers are running: `docker ps | grep -E 'scraparr|tripflow'`
- Check ports: `netstat -tlnp | grep -E '5433|5434'`

**Slow performance:**
- Increase `BATCH_SIZE` in .env (try 2000 or 5000)
- Check database IOPS: `docker stats`

**Duplicate data:**
- ETL uses UPSERT (ON CONFLICT DO UPDATE), safe to re-run
- Check: `SELECT external_id, COUNT(*) FROM tripflow.locations GROUP BY external_id HAVING COUNT(*) > 1;`

---

## Data Quality

### View Quality Metrics

```sql
SELECT
    source,
    total_records,
    completeness_score,
    records_with_description,
    records_with_images,
    records_with_coordinates
FROM tripflow.data_quality_metrics
ORDER BY metric_date DESC;
```

### Find Potential Duplicates

```sql
-- Locations within 50 meters from different sources
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

---

## Next Steps After Initial Migration

1. **Run full migration** (first time only):
   ```bash
   ssh peter@scraparr
   cd /home/peter/scraparr/etl
   venv/bin/python tripflow_etl.py
   ```

2. **Verify data**:
   ```bash
   # Should show ~221K locations
   docker exec tripflow-postgres psql -U postgres -d tripflow \
     -c 'SELECT COUNT(*) FROM tripflow.locations;'
   ```

3. **Set up daily cron** (updates from Scraparr scrapers):
   ```bash
   crontab -e
   # Add: 0 4 * * * cd /home/peter/scraparr/etl && venv/bin/python tripflow_etl.py >> cron.log 2>&1
   ```

4. **Index vectors in Qdrant** (for AI recommendations):
   ```bash
   cd /home/peter/tripflow/backend
   source venv/bin/activate
   python scripts/index_locations.py
   ```

---

## Architecture Notes

**Why separate databases?**
- Scraparr: Staging area for raw scraped data (schema per scraper)
- Tripflow: Production database with normalized schema for the app

**Why ETL instead of direct queries?**
- Data transformation (type mapping, amenities extraction)
- Deduplication across sources
- Performance (Tripflow doesn't query Scraparr in real-time)
- Data quality tracking

**Update strategy:**
- Scraparr scrapers run weekly/daily (collect new data)
- ETL runs daily at 4 AM (sync to Tripflow)
- UPSERT logic: new records inserted, existing records updated
- Tripflow app always has latest data without scraper dependencies

---

## Files

- **tripflow_etl.py** - Main ETL pipeline
- **test_etl.py** - Connection test script
- **.env** - Configuration (database URLs, batch size)
- **requirements.txt** - Python dependencies
- **venv/** - Python virtual environment
- **README.md** - Detailed documentation

---

**Status:** ✅ Ready to use
**Performance:** ~450 records/sec
**Full sync time:** 8-10 minutes
**Data:** 237K records available

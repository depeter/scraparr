# Scraparr Quick Reference

**Location**: `/home/peter/work/scraparr`

## Start/Stop

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart backend only
docker compose restart backend

# View running containers
docker ps | grep scraparr
```

## Access Points

- **Backend API**: http://192.168.1.6:8000
- **API Docs**: http://192.168.1.6:8000/docs
- **Frontend**: http://192.168.1.6:3001

## Monitoring

```bash
# Live backend logs
docker logs -f scraparr-backend

# Filter for scraping progress
docker logs -f scraparr-backend 2>&1 | grep "Progress:"

# Filter for errors
docker logs scraparr-backend --tail 200 | grep -i error

# Check database
docker exec scraparr-postgres psql -U scraparr -d scraparr
```

## Database Queries

```bash
# Quick access
docker exec -it scraparr-postgres psql -U scraparr -d scraparr

# Count places
docker exec scraparr-postgres psql -U scraparr -d scraparr -c \
  "SELECT COUNT(*) FROM scraper_2.places;"

# View recent executions
docker exec scraparr-postgres psql -U scraparr -d scraparr -c \
  "SELECT id, status, started_at, items_scraped FROM executions ORDER BY started_at DESC LIMIT 10;"

# View all jobs
docker exec scraparr-postgres psql -U scraparr -d scraparr -c \
  "SELECT id, name, is_active, next_run_at FROM jobs ORDER BY next_run_at;"
```

## API Commands

```bash
# List all jobs
curl -s http://192.168.1.6:8000/api/jobs | python3 -m json.tool

# List running executions
curl -s "http://192.168.1.6:8000/api/executions?status=running" | python3 -m json.tool

# Get job details
curl -s http://192.168.1.6:8000/api/jobs/{job_id} | python3 -m json.tool

# Pause a job
curl -X PUT http://192.168.1.6:8000/api/jobs/{job_id} \
  -H 'Content-Type: application/json' \
  -d '{"is_active": false}'

# Resume a job
curl -X PUT http://192.168.1.6:8000/api/jobs/{job_id} \
  -H 'Content-Type: application/json' \
  -d '{"is_active": true}'

# Run job immediately
curl -X POST http://192.168.1.6:8000/api/jobs/{job_id}/run
```

## Create New Job

```bash
curl -X POST http://192.168.1.6:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 2,
    "name": "My Job",
    "schedule_type": "cron",
    "schedule_config": {"expression": "0 1 * * 1"},
    "params": {
      "region": "uk",
      "grid_spacing": 0.5,
      "min_delay": 1.0,
      "max_delay": 5.0,
      "resume": true
    }
  }'
```

## Schedule Types

**Cron** (specific day/time):
```json
{
  "schedule_type": "cron",
  "schedule_config": {"expression": "0 1 * * 1"}
}
```
Format: `minute hour day_of_month month day_of_week`
- `0 1 * * 1` = Monday 1:00 AM
- `0 */6 * * *` = Every 6 hours
- `0 0 * * 0` = Sunday midnight

**Interval** (recurring):
```json
{
  "schedule_type": "interval",
  "schedule_config": {"hours": 24}
}
```
Use: `seconds`, `minutes`, `hours`, or `days`

**Once** (one-time):
```json
{
  "schedule_type": "once",
  "schedule_config": {"delay_seconds": 60}
}
```

## Scraper Parameters

```json
{
  "region": "france",        // Predefined region name
  "lat_min": 41.0,           // Or custom bounds
  "lat_max": 51.5,
  "lon_min": -5.5,
  "lon_max": 10.0,
  "grid_spacing": 0.5,       // Degrees (0.5 recommended)
  "include_reviews": false,  // Fetch reviews (slow)
  "min_delay": 1.0,          // Min API delay seconds
  "max_delay": 5.0,          // Max API delay seconds
  "resume": true             // Resume from last checkpoint
}
```

## Predefined Regions

- europe, uk, france, spain, portugal, italy, germany
- netherlands, belgium, scandinavia, alps, greece

## Troubleshooting

**Logs not showing?**
- Logs only save when scraper completes
- Use Docker logs for live monitoring: `docker logs -f scraparr-backend`

**Job not running?**
- Check `is_active`: `curl -s http://192.168.1.6:8000/api/jobs/{id} | grep is_active`
- Check `next_run_at` timestamp
- Restart backend: `docker compose restart backend`

**CORS errors?**
- Check CORS_ORIGINS in docker-compose.yml
- Restart backend after changes

**Database errors?**
- Check PostgreSQL: `docker exec scraparr-postgres pg_isready -U scraparr`
- Check logs: `docker logs scraparr-postgres`

## File Locations

- **Docker Compose**: `docker-compose.yml`
- **Backend**: `backend/`
- **Frontend**: `frontend/`
- **Scrapers**: `scrapers/park4night_scraper.py`
- **Country Jobs Script**: `/tmp/create_country_jobs.py`
- **Country Definitions**: `/tmp/europe_countries.json`

## Current State (2025-11-04)

- ✅ 29 weekly jobs scheduled (all European countries)
- ✅ 3 jobs actively running (UK, France, Italy)
- ✅ ~558+ unique places collected
- ✅ Next scheduled: Spain - Tuesday 1:00 AM

## Common Workflows

**Check progress of running jobs**:
```bash
docker logs scraparr-backend 2>&1 | grep "Progress:" | tail -10
```

**Create all country jobs**:
```bash
python3 /tmp/create_country_jobs.py
```

**Export data to CSV**:
```bash
docker exec scraparr-postgres psql -U scraparr -d scraparr -c \
  "COPY scraper_2.places TO STDOUT WITH CSV HEADER" > places.csv
```

**Backup database**:
```bash
docker exec scraparr-postgres pg_dump -U scraparr scraparr > backup.sql
```

**View job schedule**:
```bash
curl -s "http://192.168.1.6:8000/api/jobs?limit=50" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for j in sorted(data['items'], key=lambda x: x.get('next_run_at', '')):
    if j.get('next_run_at'):
        print(f\"{j['name']:40} {j['next_run_at']}\")
"
```

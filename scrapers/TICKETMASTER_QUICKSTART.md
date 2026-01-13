# Ticketmaster Scraper Quick Start

## Credentials

**API Key (Consumer Key):** `tjj2247AysyVJPd5Jnotqu2WQuCAlTIY`

Stored in: `/home/peter/work/scraparr/.ticketmaster_credentials`

## Quick Deploy Commands

### 1. Register Scraper in Scraparr

```bash
curl -X POST http://scraparr:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Ticketmaster Events",
    "description": "Ticketmaster Discovery API scraper for European events",
    "module_path": "ticketmaster_scraper",
    "class_name": "TicketmasterScraper",
    "config": {
      "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY"
    }
  }'
```

### 2. Create All Weekly Jobs (24 Countries)

```bash
cd /home/peter/work/scraparr/scrapers
export TICKETMASTER_API_KEY="tjj2247AysyVJPd5Jnotqu2WQuCAlTIY"
python create_ticketmaster_jobs.py
```

### 3. Test Single Country (UK)

```bash
# Get scraper ID first (assume it's 4)
curl -X POST http://scraparr:8000/api/scrapers/4/run \
  -H 'Content-Type: application/json' \
  -d '{
    "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
    "country_code": "GB",
    "max_events": 100,
    "size": 50
  }'
```

## One-Line Job Creation Examples

### UK - Monday 1am
```bash
curl -X POST http://scraparr:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Ticketmaster - UK Weekly",
    "params": {
      "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
      "country_code": "GB",
      "max_events": 5000,
      "size": 200
    },
    "schedule_type": "cron",
    "schedule_config": {"expression": "0 1 * * 1"}
  }'
```

### Germany - Monday 3am
```bash
curl -X POST http://scraparr:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Ticketmaster - Germany Weekly",
    "params": {
      "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
      "country_code": "DE",
      "max_events": 5000,
      "size": 200
    },
    "schedule_type": "cron",
    "schedule_config": {"expression": "0 3 * * 1"}
  }'
```

### France - Monday 4am
```bash
curl -X POST http://scraparr:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 4,
    "name": "Ticketmaster - France Weekly",
    "params": {
      "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
      "country_code": "FR",
      "max_events": 5000,
      "size": 200
    },
    "schedule_type": "cron",
    "schedule_config": {"expression": "0 4 * * 1"}
  }'
```

## Database Queries

### View scraped events
```sql
SELECT * FROM scraper_4.events ORDER BY start_date DESC LIMIT 50;
```

### Count by country
```sql
SELECT country, COUNT(*) as events FROM scraper_4.events GROUP BY country ORDER BY events DESC;
```

### Upcoming London music events
```sql
SELECT name, start_date_local, venue_name, genre, url
FROM scraper_4.events
WHERE city = 'London' AND segment = 'Music' AND start_date > NOW()
ORDER BY start_date ASC LIMIT 20;
```

## Environment Setup for Script

```bash
# Source credentials
source /home/peter/work/scraparr/.ticketmaster_credentials

# Run job creator
cd /home/peter/work/scraparr/scrapers
python create_ticketmaster_jobs.py

# Or pass directly
python create_ticketmaster_jobs.py tjj2247AysyVJPd5Jnotqu2WQuCAlTIY
```

## API Rate Limits

- **Daily**: 5,000 calls
- **Per second**: 5 requests
- **Status**: Free tier (no billing)

**Estimated coverage per day:**
- 200 events per request
- ~25 requests per country (5,000 events)
- Can scrape ~8-10 countries per day within limits

**Strategy**: Weekly schedule spreads 24 countries across 6 days = 4 countries per day

## Troubleshooting

**Check scraper exists:**
```bash
curl http://scraparr:8000/api/scrapers
```

**Check jobs:**
```bash
curl http://scraparr:8000/api/jobs
```

**Check executions:**
```bash
curl http://scraparr:8000/api/executions?scraper_id=4
```

**View logs:**
```bash
docker logs scraparr-backend --tail 100 | grep -i ticketmaster
```

## Next Steps

1. Register scraper (see command above)
2. Create weekly jobs (run script)
3. Wait for first scheduled run OR test manually
4. Check database for results
5. Query data via Scraparr UI or SQL

---

**For full documentation, see:** `TICKETMASTER_README.md`

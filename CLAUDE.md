# CLAUDE.md - Scraparr Project Guide

This file provides comprehensive guidance to Claude Code when working with the Scraparr project.

## Project Overview

**Scraparr** is a web scraping orchestration platform that manages scheduled data collection from various sources. It provides:

- **Scraper Management**: Dynamic scraper loading and execution
- **Job Scheduling**: Cron-based and interval-based job scheduling using APScheduler
- **Execution Tracking**: Monitor scraper runs, logs, and results
- **REST API**: FastAPI backend for all operations
- **React Frontend**: Web UI for managing scrapers, jobs, and executions
- **Authentication**: JWT-based authentication with user management

**Local Development Location**: `/home/peter/work/scraparr`
**Production Server Location**: `/home/peter/scraparr` (on scraparr server)

**Stack**:
- Backend: FastAPI (Python 3.11+) with async/await
- Frontend: React with TypeScript
- Database: PostgreSQL 15 with schema-per-scraper architecture
- Scheduler: APScheduler with asyncio
- Containers: Docker Compose orchestration
- Authentication: JWT tokens with bcrypt password hashing

## Server Deployment Information

### Production Server Details

**Hostname**: `scraparr` (192.168.1.149)
**User**: `peter`
**Password**: `nomansland`
**Public URL**: https://scraparr.pm-consulting.be
**Server Directory**: `/home/peter/scraparr`

**Important Path Differences**:
- Local development: `/home/peter/work/scraparr`
- Production server: `/home/peter/scraparr` (NO "work" subdirectory)

### Docker Container Architecture

**Backend Container**: `scraparr-backend`
- Host directory: `/home/peter/scraparr/backend`
- Container paths:
  - Application code: `/app/` (root)
  - App modules: `/app/app/` (for imports like `from app.models import User`)
  - Main entry: `/app/main.py`
- Volume mounts: Backend code is mounted from host
- Auto-reload: Enabled with uvicorn `--reload` flag

**Frontend Container**: `scraparr-frontend`
- Host directory: `/home/peter/scraparr/frontend`
- Build-based deployment (not live-mounted)
- Requires rebuild: `docker compose build frontend && docker compose up -d frontend`

**Database Container**: `scraparr-postgres`
- Port: 5434 (external) → 5432 (internal)
- Credentials: scraparr/scraparr
- Volume: Persistent data storage

### Deployment Workflow

**CRITICAL**: Always deploy to `/home/peter/scraparr` on the production server, NOT `/home/peter/work/scraparr`

#### Backend Deployment

Backend changes can be deployed with hot-reload:

```bash
# Setup SSH password helper
cat > /tmp/scraparr_pass.sh << 'EOF'
#!/bin/sh
echo "nomansland"
EOF
chmod +x /tmp/scraparr_pass.sh

# Copy files to server
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/api/your_file.py \
  peter@scraparr:/home/peter/scraparr/backend/app/api/

# Copy into running container for immediate effect
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker cp /home/peter/scraparr/backend/app/api/your_file.py scraparr-backend:/app/app/api/"

# Backend auto-reloads with uvicorn --reload (no restart needed)
```

**Important**:
- Files must be copied to `/app/app/` in the container (NOT `/app/backend/`)
- Python imports use `from app.models import User` → resolves to `/app/app/models/`
- Uvicorn watches `/app/` and auto-reloads on changes

#### Frontend Deployment

Frontend requires rebuild for changes:

```bash
# Copy files to server
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  frontend/src/pages/YourPage.tsx \
  peter@scraparr:/home/peter/scraparr/frontend/src/pages/

# Rebuild and restart frontend
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "cd /home/peter/scraparr && docker compose build frontend && docker compose up -d frontend"
```

#### Full Deployment Script Template

```bash
#!/bin/bash
set -e

# Setup SSH helper
cat > /tmp/scraparr_pass.sh << 'EOF'
#!/bin/sh
echo "nomansland"
EOF
chmod +x /tmp/scraparr_pass.sh

SERVER="scraparr"
USER="peter"
WORK_DIR="/home/peter/scraparr"

# Deploy backend files
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  backend/app/api/*.py \
  ${USER}@${SERVER}:${WORK_DIR}/backend/app/api/

SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh ${USER}@${SERVER} << 'ENDSSH'
cd /home/peter/scraparr

# Copy to container
docker cp backend/app/api/your_file.py scraparr-backend:/app/app/api/

# Rebuild frontend if needed
docker compose build frontend
docker compose up -d frontend
ENDSSH

# Cleanup
rm /tmp/scraparr_pass.sh
```

### Common Deployment Commands

```bash
# Check container status
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker ps | grep scraparr"

# View backend logs
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker logs scraparr-backend --tail 50"

# Restart backend (if needed)
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker restart scraparr-backend"

# Rebuild backend container (for dependency changes)
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "cd /home/peter/scraparr && docker compose build backend && docker compose up -d backend"
```

### Database Operations on Server

```bash
# Access PostgreSQL
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker exec -it scraparr-postgres psql -U scraparr -d scraparr"

# Run SQL directly
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker exec scraparr-postgres psql -U scraparr -d scraparr -c 'SELECT * FROM users;'"
```

### Troubleshooting Deployment

**Import errors after deployment**:
- Check files are in `/app/app/` not `/app/backend/` in container
- Verify `__init__.py` files include new modules
- Check container logs: `docker logs scraparr-backend --tail 50`

**Backend not reloading**:
- Ensure file was copied to container: `docker cp ... scraparr-backend:/app/app/...`
- Check uvicorn detected change: Look for "WatchFiles detected changes" in logs
- If stuck, restart container: `docker restart scraparr-backend`

**Frontend changes not visible**:
- Frontend requires full rebuild (no hot-reload)
- Clear browser cache after deployment
- Check build succeeded: `docker logs scraparr-frontend`

## Authentication System

### Overview

Scraparr uses JWT-based authentication to secure all API endpoints and frontend routes. All endpoints require authentication except for:
- `/api/auth/login` - User login
- `/api/auth/register` - New user registration

### Backend Authentication

**User Model** (`backend/app/models/user.py`):
- `username`: Unique username (3-50 chars)
- `email`: Unique email address
- `hashed_password`: Bcrypt-hashed password
- `is_active`: User account status
- `is_admin`: Admin privileges flag
- `created_at`, `updated_at`: Timestamps

**Security Module** (`backend/app/core/security.py`):
- `hash_password()`: Bcrypt password hashing
- `verify_password()`: Password verification
- `create_access_token()`: JWT token generation (30-day expiry)
- `decode_access_token()`: JWT token validation
- `get_current_user()`: FastAPI dependency for auth
- `get_current_admin_user()`: Admin-only dependency

**Auth Endpoints** (`backend/app/api/auth.py`):
- `POST /api/auth/register`: Create new user account
- `POST /api/auth/login`: Login and receive JWT token
- `GET /api/auth/me`: Get current user information

**Protected Endpoints**:
All other API endpoints require authentication via the `get_current_active_user` dependency:

```python
from app.core.security import get_current_active_user
from app.models import User

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    # Only authenticated users can access this
    return {"user": current_user.username}
```

### Frontend Authentication

**Auth Context** (`frontend/src/contexts/AuthContext.tsx`):
- Global authentication state management
- Token storage in localStorage
- Auto token validation on mount
- Login/logout functions

**Login Page** (`frontend/src/pages/LoginPage.tsx`):
- Professional login interface
- Form validation
- Error handling

**Protected Routes** (`frontend/src/components/ProtectedRoute.tsx`):
- Wraps authenticated pages
- Redirects to login if not authenticated
- Shows loading state during auth check

**API Client** (`frontend/src/api/client.ts`):
- Automatic token injection in all requests
- 401 error interception with auto-redirect to login
- Token stored as `Bearer {token}` in Authorization header

### Default Credentials

**Username**: `admin`
**Password**: `admin123`
**Email**: `admin@example.com`

**⚠️ IMPORTANT**: Change the admin password immediately after first login!

### Managing Users

**Create Admin User** (if needed):
```bash
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker exec scraparr-backend python /app/init_auth.py"
```

**Reset Admin Password**:
```bash
# Delete existing admin user
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker exec scraparr-postgres psql -U scraparr -d scraparr -c \"DELETE FROM users WHERE username='admin';\""

# Recreate with init script
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker exec scraparr-backend python /app/init_auth.py"
```

**View Users**:
```bash
SSH_ASKPASS=/tmp/scraparr_pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker exec scraparr-postgres psql -U scraparr -d scraparr -c 'SELECT id, username, email, is_active, is_admin FROM users;'"
```

### Token Details

- **Algorithm**: HS256
- **Expiry**: 30 days (43200 minutes)
- **Secret Key**: Configured in `backend/app/core/config.py`
- **Storage**: Frontend stores in localStorage as `auth_token`

### Security Considerations

- All passwords are hashed with bcrypt (bcrypt==4.0.1)
- JWT tokens expire after 30 days
- Tokens are validated on every API request
- Frontend auto-redirects to login on 401 errors
- Admin flag for future role-based access control

## Architecture

### Directory Structure

```
scraparr/
├── backend/
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   ├── scrapers.py   # Scraper CRUD endpoints
│   │   │   ├── jobs.py       # Job CRUD and scheduling
│   │   │   ├── executions.py # Execution tracking
│   │   │   ├── proxy.py      # Proxy capture endpoints
│   │   │   └── database.py   # Database query interface (read-only)
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── user.py       # User model for auth
│   │   │   ├── scraper.py
│   │   │   ├── job.py
│   │   │   └── execution.py
│   │   ├── schemas/          # Pydantic schemas
│   │   │   ├── auth.py       # Auth request/response schemas
│   │   │   └── ...
│   │   ├── core/             # Core functionality
│   │   │   ├── security.py   # Authentication & JWT
│   │   │   ├── config.py     # Application settings
│   │   │   └── database.py   # Database connection
│   │   ├── services/         # Business logic
│   │   │   ├── scheduler.py       # APScheduler management
│   │   │   └── scraper_runner.py  # Scraper execution
│   │   └── scrapers/         # Base scraper framework
│   │       └── base.py       # BaseScraper abstract class
│   ├── main.py               # FastAPI app entry point
│   └── init_auth.py          # Initialize users table & admin
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   │   └── ProtectedRoute.tsx  # Auth route guard
│   │   ├── contexts/         # React contexts
│   │   │   └── AuthContext.tsx     # Auth state management
│   │   ├── pages/            # Page components
│   │   │   ├── LoginPage.tsx       # Login interface
│   │   │   └── ...
│   │   ├── api/              # API client
│   │   │   └── client.ts     # Axios client with auth
│   │   └── types/            # TypeScript types
│   │       └── index.ts      # Auth types included
│   └── package.json
├── scrapers/                 # Scraper implementations
│   ├── park4night_scraper.py      # Park4Night grid scraper
│   └── uitinvlaanderen_scraper.py # UiT in Vlaanderen events scraper
├── docker/                   # Dockerfiles
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
└── docker-compose.yml        # Service orchestration
```

### Docker Services

**PostgreSQL Database** (`scraparr-postgres`)
- Port: 5432
- Credentials: scraparr/scraparr
- Database: scraparr
- Volume: postgres-data

**Backend API** (`scraparr-backend`)
- Port: 8000
- Environment: DEBUG=True
- Volumes: ./backend, ./scrapers (mounted for live reload)
- Command: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

**Frontend** (`scraparr-frontend`)
- Port: 3000 (or 3001 for development)
- API URL: http://localhost:8000
- Nginx-based serving in production

### Database Schema

**Schema-per-Scraper Architecture**:
- Each scraper gets its own PostgreSQL schema (e.g., `scraper_2`)
- Common tables: `scrapers`, `jobs`, `executions` in default schema
- Scraper-specific tables defined in scraper code via `define_tables()`

**Core Tables**:
```sql
-- scrapers: Registered scraper configurations
id, name, description, module_path, class_name, is_active, config

-- jobs: Scheduled scraping jobs
id, scraper_id, name, schedule_type, schedule_config, params, is_active,
last_run_at, next_run_at, scheduler_job_id

-- executions: Scraper execution history
id, scraper_id, job_id, status, started_at, completed_at,
items_scraped, error_message, logs
```

## Park4Night Scraper

### Overview

Park4Night is a camping spot database. The scraper (`park4night_scraper.py`) uses a **grid-based approach** to systematically scrape the entire database via their API.

**Key Challenges**:
1. API returns max 200 places per GPS coordinate query
2. Dense areas have thousands of overlapping places
3. Need complete coverage without duplication
4. Long-running jobs (hours) require resume capability

**Solution**: Grid-based scraping with progress tracking and deduplication.

### Scraper Classes

**`Park4NightScraper`** (Legacy, lines 1-796):
- Simple lat/lon search
- Returns up to 200 places
- Use for small targeted queries

**`Park4NightGridScraper`** (Main implementation, lines 797-1248):
- Grid-based systematic scraping
- Resume capability with progress tracking
- Automatic deduplication
- Random delays (1-5 seconds) between API calls
- **THIS IS THE ONE TO USE FOR COMPLETE DATA COLLECTION**

### Grid Scraping Implementation

**How it works**:

1. **Grid Generation**: Divide geographic region into grid points at configurable spacing (default 0.5°)
   ```python
   grid_points = []
   lat = lat_min
   while lat <= lat_max:
       lon = lon_min
       while lon <= lon_max:
           grid_points.append((lat, lon))
           lon += grid_spacing
       lat += grid_spacing
   ```

2. **API Queries**: Query Park4Night API at each grid point
   ```
   GET https://guest.park4night.com/services/V4.1/lieuxGetFilter.php
   ?latitude={lat}&longitude={lon}
   ```

3. **Deduplication**: Track seen place IDs across overlapping queries
   ```python
   seen_place_ids = set()
   for place in results:
       if place['id'] not in seen_place_ids:
           unique_places.append(place)
           seen_place_ids.add(place['id'])
   ```

4. **Progress Tracking**: Save grid progress to `grid_progress` table
   ```sql
   CREATE TABLE scraper_2.grid_progress (
       id SERIAL PRIMARY KEY,
       region VARCHAR(100),
       grid_lat FLOAT,
       grid_lon FLOAT,
       places_found INT,
       processed_at TIMESTAMP
   );
   ```

5. **Resume Capability**: Skip already-processed grid points on restart
   ```python
   if resume:
       processed = await get_processed_grid_points(region)
       grid_points = [p for p in grid_points if p not in processed]
   ```

### Predefined Regions

The scraper includes 14 predefined regions (lines 800-813):

```python
REGIONS = {
    "europe": {"lat_min": 36.0, "lat_max": 71.0, "lon_min": -10.0, "lon_max": 40.0},
    "uk": {"lat_min": 49.5, "lat_max": 61.0, "lon_min": -8.5, "lon_max": 2.0},
    "france": {"lat_min": 41.0, "lat_max": 51.5, "lon_min": -5.5, "lon_max": 10.0},
    "spain": {"lat_min": 36.0, "lat_max": 43.8, "lon_min": -9.5, "lon_max": 4.5},
    "portugal": {"lat_min": 36.8, "lat_max": 42.2, "lon_min": -9.5, "lon_max": -6.2},
    "italy": {"lat_min": 36.5, "lat_max": 47.0, "lon_min": 6.5, "lon_max": 18.5},
    "germany": {"lat_min": 47.0, "lat_max": 55.0, "lon_min": 5.5, "lon_max": 15.5},
    "netherlands": {"lat_min": 50.7, "lat_max": 53.6, "lon_min": 3.2, "lon_max": 7.3},
    "belgium": {"lat_min": 49.5, "lat_max": 51.5, "lon_min": 2.5, "lon_max": 6.5},
    "scandinavia": {"lat_min": 55.0, "lat_max": 71.2, "lon_min": 4.5, "lon_max": 31.6},
    "alps": {"lat_min": 45.0, "lat_max": 48.0, "lon_min": 5.0, "lon_max": 14.0},
    "greece": {"lat_min": 34.8, "lat_max": 41.8, "lon_min": 19.3, "lon_max": 28.3}
}
```

### Database Tables (Scraper 2)

**`scraper_2.places`** - Main place data:
```sql
id, nom, latitude, longitude, pays, note, photos, internet, electricite,
tarif, animaux_acceptes, eau_noire, type_de_lieu, stationnement,
camping_car_park, etiquettes, description, ville, updated_at, scraped_at
```

**`scraper_2.reviews`** - Place reviews:
```sql
id, place_id, author, date, rating, comment
```

**`scraper_2.grid_progress`** - Resume tracking:
```sql
id, region, grid_lat, grid_lon, places_found, processed_at
```

### Scraper Parameters

```json
{
  "region": "france",           // Predefined region or use custom bounds
  "lat_min": 41.0,              // Optional: custom latitude min
  "lat_max": 51.5,              // Optional: custom latitude max
  "lon_min": -5.5,              // Optional: custom longitude min
  "lon_max": 10.0,              // Optional: custom longitude max
  "grid_spacing": 0.5,          // Grid point spacing in degrees
  "include_reviews": false,     // Fetch reviews per place (slow)
  "min_delay": 1.0,             // Min delay between API calls (seconds)
  "max_delay": 5.0,             // Max delay between API calls (seconds)
  "resume": true                // Skip already-processed grid points
}
```

**Grid Size Estimation**:
- `grid_spacing: 0.5°` → ~4000 grid points for Europe
- `grid_spacing: 1.0°` → ~1000 grid points for Europe
- Smaller spacing = better coverage but longer runtime

**Runtime Estimates** (with 2-3 second delays):
- UK (528 grid points): ~30-45 minutes
- France (704 grid points): ~45-60 minutes
- Italy (7171 grid points): ~6-8 hours
- Full Europe (7171 grid points): ~6-8 hours

## Weekly Scraping Schedule

### Current Setup

**29 European countries** are scheduled for weekly scraping at staggered night hours (1-5 AM UTC):

| Day | Time | Countries |
|-----|------|-----------|
| Monday | 1am, 2am, 3am, 4am, 5am | UK, Ireland, France, Croatia, Lithuania |
| Tuesday | 1am, 2am, 3am, 4am | Spain, Portugal, Italy, Slovenia |
| Wednesday | 1am, 2am, 3am, 4am | Germany, Netherlands, Belgium, Bulgaria |
| Thursday | 1am, 2am, 3am, 4am | Switzerland, Austria, Norway, Serbia |
| Friday | 1am, 2am, 3am, 4am | Sweden, Finland, Denmark, Iceland |
| Saturday | 1am, 2am, 3am, 4am | Poland, Czech Republic, Slovakia, Estonia |
| Sunday | 1am, 2am, 3am, 4am | Hungary, Romania, Greece, Latvia |

**Schedule Type**: Cron expressions (weekly recurring)

**Example cron**:
- `0 1 * * 1` = Every Monday at 1:00 AM
- `0 2 * * 2` = Every Tuesday at 2:00 AM

**Created via**: `/tmp/create_country_jobs.py` (uses `/tmp/europe_countries.json`)

### Job Configuration

Each country job is configured as:

```json
{
  "scraper_id": 2,
  "name": "Park4Night - France Weekly",
  "description": "Weekly scrape of France - Monday at 3:00 AM",
  "params": {
    "region": "france",
    "lat_min": 41.0,
    "lat_max": 51.5,
    "lon_min": -5.5,
    "lon_max": 10.0,
    "grid_spacing": 0.5,
    "include_reviews": false,
    "min_delay": 1.0,
    "max_delay": 5.0,
    "resume": true
  },
  "schedule_type": "cron",
  "schedule_config": {
    "expression": "0 3 * * 1"
  }
}
```

## Job Scheduling System

### Schedule Types

**1. Once** - Run once at specific time:
```json
{
  "schedule_type": "once",
  "schedule_config": {
    "delay_seconds": 60  // Run in 60 seconds
  }
}
```
OR
```json
{
  "schedule_type": "once",
  "schedule_config": {
    "run_at": "2025-01-01T12:00:00Z"  // Specific datetime
  }
}
```

**2. Interval** - Recurring at fixed intervals:
```json
{
  "schedule_type": "interval",
  "schedule_config": {
    "seconds": 3600  // Every hour
  }
}
```
OR use `"minutes"`, `"hours"`, or `"days"` instead of `"seconds"`.

**3. Cron** - Cron expression scheduling:
```json
{
  "schedule_type": "cron",
  "schedule_config": {
    "expression": "0 1 * * 1"  // Every Monday at 1:00 AM
  }
}
```

**Cron format**: `minute hour day_of_month month day_of_week`
- Day of week: 0 = Sunday, 1 = Monday, ..., 6 = Saturday

### APScheduler Implementation

Located in `backend/app/services/scheduler.py`:

**Key Methods**:
- `add_job()` - Add job to scheduler
- `remove_job()` - Remove job from scheduler
- `reload_jobs()` - Load all active jobs from database on startup
- `_create_trigger()` - Convert schedule config to APScheduler trigger
- `_execute_scraper()` - Called by scheduler to run scraper

**Trigger Mapping**:
- `cron` → `CronTrigger`
- `interval` → `IntervalTrigger`
- `once` → `DateTrigger`

## API Reference

### Base URL
`http://192.168.1.6:8000` (or `http://localhost:8000`)

### Scrapers

**List scrapers**:
```
GET /api/scrapers?skip=0&limit=100
```

**Get scraper**:
```
GET /api/scrapers/{scraper_id}
```

**Create scraper**:
```
POST /api/scrapers
{
  "name": "My Scraper",
  "description": "Description",
  "module_path": "park4night_scraper",
  "class_name": "Park4NightGridScraper",
  "config": {}
}
```

**Run scraper immediately**:
```
POST /api/scrapers/{scraper_id}/run
{
  "region": "uk",
  "grid_spacing": 0.5
}
```

### Jobs

**List jobs**:
```
GET /api/jobs?skip=0&limit=100
```

**Create job**:
```
POST /api/jobs
{
  "scraper_id": 2,
  "name": "Weekly UK Scrape",
  "schedule_type": "cron",
  "schedule_config": {"expression": "0 1 * * 1"},
  "params": {"region": "uk"}
}
```

**Update job**:
```
PUT /api/jobs/{job_id}
{
  "is_active": false  // Pause job
}
```

**Delete job**:
```
DELETE /api/jobs/{job_id}
```

**Run job manually**:
```
POST /api/jobs/{job_id}/run
```

### Executions

**List executions**:
```
GET /api/executions?skip=0&limit=100&status=completed
```

**Get execution details**:
```
GET /api/executions/{execution_id}
```

**Get execution logs**:
```
GET /api/executions/{execution_id}/logs
```

**Execution statuses**:
- `pending` - Queued but not started
- `running` - Currently executing
- `completed` - Finished successfully
- `failed` - Encountered error

### Database Query Interface

**IMPORTANT**: Read-only database access for exploration and debugging.

**List schemas**:
```
GET /api/database/schemas
```

**List tables** (optionally filtered by schema):
```
GET /api/database/tables
GET /api/database/tables?schema=scraper_3
```

**List columns** for a specific table:
```
GET /api/database/columns/{schema}/{table}
GET /api/database/columns/scraper_3/events
```

**Execute query** (SELECT only):
```
POST /api/database/query
{
  "query": "SELECT * FROM scraper_3.events LIMIT 10",
  "limit": 1000
}
```

**Security features**:
- Only SELECT statements allowed
- Dangerous keywords blocked (DROP, DELETE, UPDATE, INSERT, CREATE, ALTER, TRUNCATE, GRANT, REVOKE)
- 30-second query timeout
- Default 1000 row limit (configurable per query)
- Auto-appends LIMIT if not specified

**Frontend access**: Navigate to `/database` page for visual query interface with schema browser, SQL editor, and results table.

## UiT in Vlaanderen Scraper

### Overview

UiT in Vlaanderen is Belgium's cultural event database. The scraper (`uitinvlaanderen_scraper.py`) uses the **public GraphQL API** to collect event data without authentication.

**Key Details**:
- API: `https://api.uit.be/graphql`
- No authentication required
- Hard pagination limit: 10,000 events (start + limit ≤ 10,000)
- Rate limiting: 1-5 second delays between requests
- Schema: `scraper_3`

### API Architecture

**GraphQL Endpoint**: Public, no API key needed (unlike the paid REST API)

**Query Structure**:
```graphql
query GetEvents($limit: Float, $offset: Float) {
  events(limit: $limit, offset: $offset) {
    totalItems
    data {
      ... on Event {
        id
        name
        description
        location { name, address { streetAddress, locality, postalCode }, geo { lat, lng } }
        images { url }
        calendar { startDate, endDate }
        types { name }
        themes { name }
        organizer { name }
      }
    }
  }
}
```

### Scraper Implementation

**Class**: `UiTinVlaanderenScraper` (extends `BaseScraper`)

**Scraper Type**: `ScraperType.API`

**Key Features**:
1. Pagination with 10,000 event hard limit
2. Rate limiting (1-5 second delays)
3. Proper logging via `self.log()` (not `logger.info()`)
4. Graceful handling of missing geo data
5. Automatic offset tracking

**Parameters**:
```python
{
  "max_results": 10000,      # Max events to scrape (capped at 10,000)
  "limit_per_page": 50,      # Events per API request (max 100)
  "query": "concert",        # Optional text search
  "postal_codes": ["9000"],  # Optional postal code filter
  "region": "Gent"           # Optional region filter (not fully implemented)
}
```

### Database Tables (Schema: scraper_3)

**`scraper_3.events`** - Event data:
```sql
id, event_id (unique), name, description, start_date, end_date,
location_name, street_address, city, postal_code, country,
latitude, longitude, organizer, event_type, themes, url, image_url,
scraped_at, updated_at
```

**Fields**:
- `event_id`: UiT database ID (unique across scrapes)
- `city`: Indexed for fast location queries
- `event_type`: Indexed (Concert, Festival, Theater, etc.)
- `themes`: Comma-separated theme names
- `country`: Always 'BE' (Belgium)
- `url`: Direct link to uitinvlaanderen.be event page

### Current Schedule

**Job**: UiT Vlaanderen - Daily Events
**Schedule**: Daily at 2:00 AM (cron: `0 2 * * *`)
**Parameters**:
```json
{
  "max_results": 10000,
  "limit_per_page": 50,
  "min_delay": 1.0,
  "max_delay": 5.0
}
```

**Runtime**: ~10 minutes for 10,000 events with 1-5 second delays

### Important Implementation Notes

**Logging**:
- ✅ **CORRECT**: `self.log("message")` - Stored in database, visible in UI
- ❌ **WRONG**: `logger.info("message")` - Only in Docker logs, not in UI

**Error Handling**:
```python
# Handle missing geo data
geo = location.get('geo')
latitude = geo.get('lat') if geo else None  # Prevents AttributeError
longitude = geo.get('lng') if geo else None
```

**API Pagination Limits**:
```python
# Check for API limit
if offset + limit_per_page > 10000:
    self.log(f"Approaching API pagination limit, stopping", level="warning")
    break
```

### Data Quality

**Coverage**: ~69,295 total events available in UiT database (as of Nov 2025)
**Completeness**: 10,000 event limit means only most recent/relevant events
**Update Strategy**: Daily refresh replaces old data with current events

### Troubleshooting

**No logs in UI**:
- Check scraper uses `self.log()` not `logger.info()`
- Logs only saved to database after scraper completes

**GraphQL errors**:
- `404: Parameters start + limit must be <= 10000` → Reduce max_results or check offset
- `'NoneType' object has no attribute 'get'` → Check for None before calling `.get()`

**No events scraped**:
- Check API is accessible: `curl https://api.uit.be/graphql`
- Verify GraphQL query syntax
- Check execution logs for errors

## Ticketmaster Scraper

### Overview

Ticketmaster is the world's largest ticket marketplace. The scraper (`ticketmaster_scraper.py`) uses the **Ticketmaster Discovery API v2** to collect event data across European countries.

**Key Details**:
- API: `https://app.ticketmaster.com/discovery/v2/events.json`
- Requires free API key from https://developer.ticketmaster.com/
- Rate limits: 5,000 calls/day, 5 requests/second (free tier)
- Schema: `scraper_4`
- 24 European countries supported

**Credentials**:
- API Key: `tjj2247AysyVJPd5Jnotqu2WQuCAlTIY`
- Stored in: `/home/peter/work/scraparr/.ticketmaster_credentials`

### API Architecture

**REST API Endpoint**: Official public API with comprehensive documentation

**Key Features**:
```
GET https://app.ticketmaster.com/discovery/v2/events.json
  ?apikey=YOUR_KEY
  &countryCode=GB
  &size=200
  &page=0
  &sort=date,asc
```

**Response**: JSON with events array, pagination info, and embedded venue/promoter data

### Scraper Implementation

**Class**: `TicketmasterScraper` (extends `BaseScraper`)

**Scraper Type**: `ScraperType.API`

**Key Features**:
1. Automatic pagination (200 events per page, unlimited pages)
2. Rate limiting (0.5-2 second delays)
3. 429 error handling (60-second backoff)
4. Proper logging via `self.log()`
5. Rich event data (venue, pricing, genres, promoters)
6. Automatic deduplication

**Parameters**:
```python
{
  "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",  # Required
  "country_code": "GB",          # ISO code or "all" for all EU countries
  "city": "London",              # Optional city filter
  "keyword": "rock",             # Optional search keyword
  "segment_name": "Music",       # Optional: Music, Sports, Arts & Theatre, Film
  "genre_id": "KnvZfZ7vAeA",     # Optional Ticketmaster genre ID
  "start_date": "2025-12-01T00:00:00Z",  # Optional date range
  "end_date": "2025-12-31T23:59:59Z",
  "size": 200,                   # Events per page (max 200)
  "max_events": 5000,            # Maximum total events
  "min_delay": 0.5,              # Min delay between requests
  "max_delay": 2.0               # Max delay between requests
}
```

### Database Tables (Schema: scraper_4)

**`scraper_4.events`** - Event data:
```sql
id, event_id (unique), name, description, url, info,
start_date, start_date_local, timezone, status_code,
venue_id, venue_name, venue_address, city, postal_code,
country, country_code, latitude, longitude,
price_min, price_max, currency,
genre, segment, classifications (JSON),
promoter_id, promoter_name,
image_url, image_ratio,
external_links (JSON),
scraped_at, updated_at
```

**Key Fields**:
- `event_id`: Ticketmaster event ID (unique across scrapes)
- `start_date`: DateTime in UTC
- `start_date_local`: Local date/time string
- `latitude`/`longitude`: Venue coordinates
- `segment`: Event category (Music, Sports, Arts & Theatre, etc.)
- `genre`: Specific genre (Rock, Pop, Football, etc.)
- `classifications`: Full JSON of all classifications
- `external_links`: Social media links as JSON

### Supported Countries

24 European countries with Ticketmaster presence:

- Austria (AT)
- Belgium (BE)
- Bulgaria (BG)
- Croatia (HR)
- Czech Republic (CZ)
- Denmark (DK)
- Finland (FI)
- France (FR)
- Germany (DE)
- Greece (GR)
- Hungary (HU)
- Iceland (IS)
- Ireland (IE)
- Italy (IT)
- Netherlands (NL)
- Norway (NO)
- Poland (PL)
- Portugal (PT)
- Romania (RO)
- Spain (ES)
- Sweden (SE)
- Switzerland (CH)
- Turkey (TR)
- United Kingdom (GB)

### Current Schedule

**Recommended**: Weekly scraping spread across 6 days (Monday-Saturday)

**Schedule Creation**:
```bash
cd /home/peter/work/scraparr/scrapers
export TICKETMASTER_API_KEY="tjj2247AysyVJPd5Jnotqu2WQuCAlTIY"
python create_ticketmaster_jobs.py
```

**Creates 24 jobs**:
- **Monday (1-4am)**: UK, Ireland, Germany, France
- **Tuesday (1-4am)**: Spain, Italy, Netherlands, Belgium
- **Wednesday (1-4am)**: Switzerland, Austria, Sweden, Norway
- **Thursday (1-4am)**: Denmark, Finland, Poland, Czech Republic
- **Friday (1-4am)**: Portugal, Greece, Hungary, Romania
- **Saturday (1-4am)**: Croatia, Bulgaria, Turkey, Iceland

**Runtime**: ~15-25 minutes per country for 5,000 events

### Important Implementation Notes

**API Rate Limits**:
- Free tier: 5,000 calls/day, 5 requests/second
- 200 events per request
- Can scrape ~1,000,000 events per day theoretically
- Weekly schedule uses ~100 requests per country (~2,400/week total)

**Error Handling**:
```python
# Handle 429 rate limit errors
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        self.log(f"Rate limited, waiting 60 seconds...", level="warning")
        await asyncio.sleep(60)
        continue
```

**Pagination**:
```python
# API returns pagination info
page_data = data.get('page', {})
total_pages = page_data.get('totalPages', 1)
total_elements = page_data.get('totalElements', 0)
```

### Data Quality

**Coverage**: Typically 1,000-10,000 events per country
**Update Frequency**: Weekly recommended to catch new events
**Completeness**: Official source, most comprehensive for major venues

**Event Types**:
- Music: Concerts, festivals, tours
- Sports: Football, basketball, tennis, etc.
- Arts & Theatre: Theater, ballet, opera
- Film: Cinema, film festivals
- Miscellaneous: Comedy, family events, exhibitions

### Usage Examples

**Example 1: Scrape all UK events**:
```json
{
  "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
  "country_code": "GB",
  "max_events": 5000
}
```

**Example 2: London music events**:
```json
{
  "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
  "country_code": "GB",
  "city": "London",
  "segment_name": "Music",
  "max_events": 2000
}
```

**Example 3: Upcoming football in Germany**:
```json
{
  "api_key": "tjj2247AysyVJPd5Jnotqu2WQuCAlTIY",
  "country_code": "DE",
  "keyword": "football",
  "segment_name": "Sports",
  "start_date": "2025-12-01T00:00:00Z"
}
```

### Troubleshooting

**401 Unauthorized**:
- Check API key is correct
- Verify app is activated at https://developer.ticketmaster.com/

**429 Rate Limited**:
- Wait for daily limit reset (midnight UTC)
- Increase delays: `min_delay: 1.0, max_delay: 3.0`
- Reduce max_events per job

**No events found**:
- Try without filters first (just country_code)
- Check Ticketmaster website for event availability
- Verify city name spelling

**Import errors**:
- Ensure scraper file is in `/home/peter/work/scraparr/scrapers/`
- Check `from app.scrapers.base import BaseScraper` works
- Verify Python path includes backend directory

### Documentation

- **Full Documentation**: `/home/peter/work/scraparr/scrapers/TICKETMASTER_README.md`
- **Quick Start Guide**: `/home/peter/work/scraparr/scrapers/TICKETMASTER_QUICKSTART.md`
- **Credentials**: `/home/peter/work/scraparr/.ticketmaster_credentials`
- **Job Creator**: `/home/peter/work/scraparr/scrapers/create_ticketmaster_jobs.py`

### API Documentation

**Official Docs**: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/

**Key Endpoints**:
- Events Search: `/discovery/v2/events.json`
- Event Details: `/discovery/v2/events/{id}.json`
- Classifications: `/discovery/v2/classifications.json`

## Deployment to Scraparr Server

### Server Details

**Hostname**: `scraparr` (192.168.1.149)
**User**: peter
**Password**: nomansland
**Public URL**: https://scraparr.pm-consulting.be
**Location**: `/home/peter/work/scraparr`

### Deployment Process

**IMPORTANT**: The Docker container uses `/app/app` for imports (from the Docker image), NOT `/app/backend` (the mounted volume). Files must be copied into the running container for immediate effect.

**Quick deployment steps**:

1. **Copy files to server**:
```bash
# Setup SSH password helper
cat > /tmp/pass.sh << 'EOF'
#!/bin/sh
echo "nomansland"
EOF
chmod +x /tmp/pass.sh

# Copy backend files
SSH_ASKPASS=/tmp/pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  /home/peter/work/scraparr/backend/app/api/database.py \
  peter@scraparr:/home/peter/work/scraparr/backend/app/api/database.py

# Copy frontend files
SSH_ASKPASS=/tmp/pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force scp \
  /home/peter/work/scraparr/frontend/src/pages/DatabasePage.tsx \
  peter@scraparr:/home/peter/work/scraparr/frontend/src/pages/DatabasePage.tsx
```

2. **Copy into running backend container** (for immediate effect):
```bash
SSH_ASKPASS=/tmp/pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "docker cp /home/peter/work/scraparr/backend/app/api/database.py scraparr-backend:/app/app/api/database.py"

# Backend auto-reloads with uvicorn --reload
```

3. **Rebuild frontend** (React changes require rebuild):
```bash
SSH_ASKPASS=/tmp/pass.sh DISPLAY=:0 SSH_ASKPASS_REQUIRE=force ssh peter@scraparr \
  "cd /home/peter/work/scraparr && docker compose build frontend && docker compose up -d frontend"
```

### Docker Container Paths

**Backend**:
- Image path (used for imports): `/app/app/`
- Volume mount path: `/app/backend/`
- **Import behavior**: `from app.api import database` → `/app/app/api/database.py`

**Frontend**:
- Build path: `/app/build` (inside container during build)
- Nginx serves from: `/usr/share/nginx/html`
- **Deployment**: Requires full rebuild for React changes

### Common Deployment Commands

**Backend hot-reload** (copy into container):
```bash
# Via SSH to server, then docker cp
ssh peter@scraparr "docker cp /home/peter/work/scraparr/backend/main.py scraparr-backend:/app/main.py"
```

**Backend restart**:
```bash
ssh peter@scraparr "cd /home/peter/work/scraparr && docker compose restart backend"
```

**Frontend rebuild & deploy**:
```bash
ssh peter@scraparr "cd /home/peter/work/scraparr && docker compose build frontend && docker compose up -d frontend"
```

**Check logs**:
```bash
ssh peter@scraparr "docker logs scraparr-backend --tail 50"
ssh peter@scraparr "docker logs scraparr-frontend --tail 50"
```

**Verify deployment**:
```bash
# Test backend API
curl -s http://scraparr:8000/api/scrapers | python3 -m json.tool

# Test database endpoint
curl -s http://scraparr:8000/api/database/schemas

# Check frontend
curl -s http://scraparr:3001/ | grep -o '<title>.*</title>'
```

### Updating __init__.py Files

When adding new API modules, remember to update `backend/app/api/__init__.py`:

```python
"""API routes"""
from . import scrapers, jobs, executions, proxy, database

__all__ = ["scrapers", "jobs", "executions", "proxy", "database"]
```

Then copy to both host and container:
```bash
# Copy to host
scp backend/app/api/__init__.py peter@scraparr:/home/peter/work/scraparr/backend/app/api/__init__.py

# Copy to container
ssh peter@scraparr "docker cp /home/peter/work/scraparr/backend/app/api/__init__.py scraparr-backend:/app/app/api/__init__.py"
```

### Troubleshooting Deployment

**404 Not Found on new endpoints**:
- Check `__init__.py` includes the new module
- Verify file exists in container: `docker exec scraparr-backend ls /app/app/api/`
- Check backend logs for import errors

**Frontend changes not visible**:
- Frontend requires full rebuild (not hot-reload)
- Check build succeeded: `docker logs scraparr-frontend`
- Clear browser cache

**Backend not reloading**:
- Uvicorn watches `/app/` directory
- Copy files to `/app/` not `/app/backend/` for auto-reload
- Check logs for "WatchFiles detected changes" message

## Common Tasks

### Start the Application

```bash
cd /home/peter/work/scraparr
docker compose up -d
```

Access:
- Backend API: http://scraparr.pm-consulting.be/api (or http://192.168.1.149:8000)
- API Docs: http://192.168.1.149:8000/docs
- Frontend: https://scraparr.pm-consulting.be (or http://192.168.1.149:3001)
- Database Explorer: https://scraparr.pm-consulting.be/database

### View Logs

```bash
# Backend logs
docker logs scraparr-backend --tail 100 -f

# Filter for scraper activity
docker logs scraparr-backend 2>&1 | grep -E "Grid point|Progress:"

# Frontend logs
docker logs scraparr-frontend --tail 100 -f

# Database logs
docker logs scraparr-postgres --tail 100 -f
```

### Monitor Running Scrapers

**Live progress updates**:
```bash
docker logs -f scraparr-backend 2>&1 | grep "Progress:"
```

**Check database**:
```bash
docker exec scraparr-postgres psql -U scraparr -d scraparr -c "
SELECT COUNT(*) FROM scraper_2.places;
"
```

**Check running executions**:
```bash
curl -s "http://192.168.1.6:8000/api/executions?status=running" | python3 -m json.tool
```

### Create Weekly Country Jobs

**Using prepared script**:
```bash
python3 /tmp/create_country_jobs.py
```

**Manual creation**:
```bash
curl -X POST http://192.168.1.6:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 2,
    "name": "Park4Night - UK Weekly",
    "description": "Weekly scrape of UK",
    "params": {
      "region": "uk",
      "grid_spacing": 0.5,
      "min_delay": 1.0,
      "max_delay": 5.0,
      "resume": true
    },
    "schedule_type": "cron",
    "schedule_config": {
      "expression": "0 1 * * 1"
    }
  }'
```

### Database Operations

**Access PostgreSQL**:
```bash
docker exec -it scraparr-postgres psql -U scraparr -d scraparr
```

**Common queries**:
```sql
-- List all scrapers
SELECT id, name, class_name, is_active FROM scrapers;

-- List all jobs
SELECT id, name, schedule_type, is_active, next_run_at FROM jobs;

-- Recent executions
SELECT id, scraper_id, status, started_at, items_scraped
FROM executions
ORDER BY started_at DESC
LIMIT 10;

-- Place statistics
SELECT
  pays as country,
  COUNT(*) as total_places,
  AVG(note) as avg_rating
FROM scraper_2.places
GROUP BY pays
ORDER BY total_places DESC;

-- Grid progress
SELECT
  region,
  COUNT(*) as grid_points_processed,
  SUM(places_found) as total_places_found
FROM scraper_2.grid_progress
GROUP BY region;
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart backend only
docker compose restart backend

# Rebuild and restart
docker compose up -d --build backend
```

### Stop Running Jobs

**Via API**:
```bash
# Get job ID from /api/jobs
curl -X PUT http://192.168.1.6:8000/api/jobs/{job_id} \
  -H 'Content-Type: application/json' \
  -d '{"is_active": false}'
```

**Via Docker** (nuclear option):
```bash
docker compose restart backend
```

Note: Long-running scrapers can be stopped and resumed thanks to `resume: true` parameter.

## Development

### Adding a New Scraper

1. **Create scraper file** in `scrapers/`:
```python
from app.scrapers.base import BaseScraper

class MyNewScraper(BaseScraper):
    async def scrape(self, params: dict):
        # Your scraping logic here
        results = []
        # ... scrape data ...
        return results

    def define_tables(self):
        # Define your database tables
        from sqlalchemy import Table, Column, Integer, String

        my_table = Table(
            'my_data',
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(255)),
            extend_existing=True,
            schema=self.schema_name
        )
        return [my_table]

    async def after_scrape(self, results, params):
        # Save results to database
        engine = self.get_engine()
        tables = self.define_tables()
        my_table = tables[0]

        async with engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)
            for item in results:
                await conn.execute(
                    my_table.insert().values(**item)
                )
```

2. **Register scraper** via API:
```bash
curl -X POST http://192.168.1.6:8000/api/scrapers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "My New Scraper",
    "module_path": "my_new_scraper",
    "class_name": "MyNewScraper"
  }'
```

3. **Create job**:
```bash
curl -X POST http://192.168.1.6:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "scraper_id": 3,
    "name": "My Scraper Job",
    "schedule_type": "interval",
    "schedule_config": {"hours": 24},
    "params": {}
  }'
```

### Live Reload Development

Backend and frontend have live reload enabled when running via Docker Compose:

**Backend**: Mounted volumes auto-reload on file changes
```bash
docker logs -f scraparr-backend  # Watch for "Reloading..."
```

**Frontend**: React dev server auto-reloads
```bash
docker logs -f scraparr-frontend
```

### Testing API Endpoints

**Using curl**:
```bash
curl -s http://192.168.1.6:8000/api/scrapers | python3 -m json.tool
```

**Using browser** (Interactive API docs):
```
http://192.168.1.6:8000/docs
```

**Using test HTML file**:
```
file:///home/peter/work/scraparr/test-api.html
```

## Troubleshooting

### Logs Show "No logs available"

**Cause**: Logs are only saved to database when scraper **completes**. Long-running grid scrapers won't show logs until finished.

**Solution**: Monitor live logs via Docker:
```bash
docker logs -f scraparr-backend 2>&1 | grep "Progress:"
```

### Jobs Not Running

**Check job is active**:
```bash
curl -s http://192.168.1.6:8000/api/jobs/{job_id} | grep is_active
```

**Check next run time**:
```bash
curl -s http://192.168.1.6:8000/api/jobs/{job_id} | grep next_run_at
```

**Check backend logs**:
```bash
docker logs scraparr-backend 2>&1 | grep "Scheduler"
```

**Reload jobs**:
```bash
docker compose restart backend
```

### CORS Errors in Frontend

**Check CORS_ORIGINS** in `docker-compose.yml`:
```yaml
environment:
  CORS_ORIGINS: '["http://localhost:3000", "http://192.168.1.6:3000", "http://192.168.1.6:3001"]'
```

**Restart backend**:
```bash
docker compose restart backend
```

### Database Connection Errors

**Check PostgreSQL is running**:
```bash
docker ps | grep postgres
```

**Check database health**:
```bash
docker exec scraparr-postgres pg_isready -U scraparr
```

**Check connection string** in backend environment:
```yaml
DATABASE_URL: postgresql+asyncpg://scraparr:scraparr@postgres:5432/scraparr
```

### Scraper Crashes or Errors

**Check execution logs**:
```bash
curl -s http://192.168.1.6:8000/api/executions?status=failed | python3 -m json.tool
```

**Check backend logs**:
```bash
docker logs scraparr-backend --tail 200 | grep -A 10 "ERROR"
```

**Common issues**:
1. **Table already exists**: Add `extend_existing=True` to Table definitions
2. **Duplicate index**: Remove `index=True` from Column definitions if index already exists
3. **Schema not created**: Ensure `create_all()` is called in `after_scrape()`
4. **API rate limiting**: Increase `min_delay` and `max_delay` parameters

## Important Files

### Configuration Files

- `docker-compose.yml` - Service orchestration
- `backend/requirements.txt` - Python dependencies
- `frontend/package.json` - Node.js dependencies

### Country Definitions

- `/tmp/europe_countries.json` - 29 European countries with coordinates and schedules
- `/tmp/create_country_jobs.py` - Script to create weekly jobs for all countries

### Scraper Implementations

- `scrapers/park4night_scraper.py` - Park4Night grid scraper (scraper_2)
- `scrapers/uitinvlaanderen_scraper.py` - UiT in Vlaanderen GraphQL scraper (scraper_3)
- `scrapers/ticketmaster_scraper.py` - Ticketmaster Discovery API scraper (scraper_4)
- `scrapers/eventbrite_scraper.py` - Eventbrite web scraper (not yet registered)

### Key Backend Files

- `backend/main.py` - FastAPI app entry point
- `backend/app/api/database.py` - Database query interface (read-only)
- `backend/app/services/scheduler.py` - APScheduler management
- `backend/app/services/scraper_runner.py` - Scraper execution engine
- `backend/app/scrapers/base.py` - BaseScraper abstract class

### Key Frontend Files

- `frontend/src/App.tsx` - Main app with routing and navigation
- `frontend/src/pages/DatabasePage.tsx` - Database query interface page
- `frontend/src/pages/ScrapersPage.tsx` - Scraper management page
- `frontend/src/pages/JobsPage.tsx` - Job management page
- `frontend/src/pages/ExecutionsPage.tsx` - Execution history page

## Data Collection Strategy

### Rate Limiting

**Why it matters**: Respectful scraping prevents IP bans and server overload.

**Implementation**:
```python
min_delay = params.get("min_delay", 1.0)
max_delay = params.get("max_delay", 5.0)
delay = random.uniform(min_delay, max_delay)
await asyncio.sleep(delay)
```

**Recommended values**:
- `min_delay: 1.0` - Minimum 1 second between requests
- `max_delay: 5.0` - Maximum 5 seconds between requests
- Average: ~3 seconds per request
- ~1200 requests per hour

### Deduplication Strategy

Grid-based scraping creates overlapping queries. Deduplication prevents duplicate database entries:

```python
seen_place_ids = set()

for place in api_results:
    place_id = place['id']
    if place_id not in seen_place_ids:
        unique_places.append(place)
        seen_place_ids.add(place_id)
```

**Why necessary**:
- Place at (50.5, 4.5) may appear in queries for (50.0, 4.0), (50.0, 4.5), (50.5, 4.0), (50.5, 4.5)
- Without deduplication: 4x duplicate data
- With deduplication: 1x clean data

### Resume Capability

Long-running scrapers can be interrupted and resumed:

```python
if resume:
    # Get already-processed grid points
    processed = await get_processed_grid_points(region)
    # Filter them out
    grid_points = [p for p in grid_points if p not in processed]
```

**Benefits**:
- Scraper can be stopped/restarted without losing progress
- Failed runs can continue from last checkpoint
- Allows incremental scraping of huge regions

**Progress tracking** in `grid_progress` table:
```sql
INSERT INTO scraper_2.grid_progress
(region, grid_lat, grid_lon, places_found, processed_at)
VALUES ('france', 45.5, 3.0, 87, NOW());
```

## Current State (as of 2025-11-21)

### Infrastructure
- ✅ Docker Compose setup running on remote server (scraparr.pm-consulting.be)
- ✅ PostgreSQL database operational
- ✅ FastAPI backend with hot reload
- ✅ React frontend with production build (Nginx)
- ✅ CORS configured for production
- ✅ Database query interface deployed
- ✅ Authentication system with JWT tokens

### Scrapers
- ✅ **Park4Night** grid scraper fully implemented (scraper_2)
  - Resume capability working
  - Random delays (1-5s) implemented
  - Deduplication across grid queries working
  - 14 predefined regions available

- ✅ **UiT in Vlaanderen** GraphQL scraper implemented (scraper_3)
  - Public API, no authentication required
  - Proper logging via `self.log()`
  - 10,000 event pagination limit handled
  - Missing geo data gracefully handled

- ✅ **Ticketmaster** Discovery API scraper implemented (scraper_4)
  - Official API with free tier (5,000 calls/day)
  - 24 European countries supported
  - Rich event data (venue, pricing, genres, promoters)
  - Rate limiting and 429 error handling
  - Automatic pagination (200 events/page)
  - Ready for deployment

### Jobs
- ✅ Park4Night: 29 European country jobs (weekly schedules, Mon-Sun 1-5 AM)
- ✅ UiT in Vlaanderen: Daily scrape at 2:00 AM (10,000 events)
- 🔧 Ticketmaster: 24 country jobs ready to create (via script)
- ✅ APScheduler managing all jobs with auto-reload

### Data
- ✅ **scraper_2**: Park4Night places, reviews, grid_progress
- ✅ **scraper_3**: UiT in Vlaanderen events (~10,000 events daily)
- 🔧 **scraper_4**: Ticketmaster events (ready to populate)
- ✅ Database query interface for read-only SQL access

### Features
- ✅ **Database Explorer** (frontend `/database` page)
  - Schema browser with table/column viewer
  - SQL query editor with syntax validation
  - Results table with execution time display
  - Quick query buttons
  - Read-only security (SELECT only)
- ✅ **Logs in UI** - Scrapers use `self.log()` for UI-visible logs
- ✅ **API Documentation** at `/docs`

### Known Limitations
- ⚠️ Logs only available after scraper completes (not live streaming)
- ⚠️ Long-running jobs (6+ hours for large countries)
- ⚠️ No UI progress indicator for running jobs
- ⚠️ UiT API has 10,000 event pagination limit (can't fetch all 69,295+ events)

## Future Improvements

### High Priority
1. **Live log streaming**: WebSocket-based real-time logs
2. **Progress API endpoint**: Return current progress for running jobs
3. **Job pause/resume**: Gracefully stop and resume long-running scrapers
4. **Scraper name in executions**: Fix foreign key relationship

### Medium Priority
5. **Rate limit monitoring**: Track API calls per hour/day
6. **Error recovery**: Automatic retry for failed grid points
7. **Data validation**: Verify scraped data completeness
8. **Export functionality**: CSV/JSON export of scraped data

### Low Priority
9. **Email notifications**: Alert on job completion/failure
10. **Metrics dashboard**: Visualize scraping progress and data growth
11. **API key management**: Secure API credentials
12. **Multi-threaded scraping**: Parallel grid point processing

## External Resources

**Park4Night API**:
- Repository: https://github.com/gtoselli/park4night-api
- Endpoint: `https://guest.park4night.com/services/V4.1/lieuxGetFilter.php`
- Rate limits: Unknown (using conservative 1-5 second delays)

**UiT in Vlaanderen API**:
- GraphQL Endpoint: https://api.uit.be/graphql
- Documentation: https://docs.publiq.be/ and https://documentatie.uitdatabank.be/
- Public access: No authentication required
- Website: https://www.uitinvlaanderen.be

**Technologies**:
- FastAPI: https://fastapi.tiangolo.com/
- APScheduler: https://apscheduler.readthedocs.io/
- SQLAlchemy: https://www.sqlalchemy.org/
- React: https://react.dev/
- Material-UI: https://mui.com/

## Contact & Support

**Project Location**: `/home/peter/work/scraparr`

**Owner**: peter

**Common Commands Quick Reference**:
```bash
# Start
docker compose up -d

# Logs
docker logs -f scraparr-backend

# Database
docker exec -it scraparr-postgres psql -U scraparr -d scraparr

# API
curl http://192.168.1.6:8000/api/jobs

# Monitor
docker logs -f scraparr-backend 2>&1 | grep "Progress:"
```

# Scraparr

Advanced web scraping management system with scheduling, multi-database support, and a modern management interface.

**Current Focus**: Scraping Park4Night camping database across 29 European countries with weekly automated jobs.

## Features

- **React Frontend**: Modern, responsive management interface for creating, scheduling, and monitoring scraping jobs
- **Python Backend**: FastAPI-based REST API with async support
- **Multi-Database Architecture**: Separate PostgreSQL schemas for each scraped site
- **Flexible Scrapers**: Support for both API interactions and web page scraping
- **Job Scheduler**: Schedule scraping jobs with cron-like expressions
- **Job Monitoring**: Real-time status updates and execution history
- **Custom Logic**: Write custom scraper logic in Python with a simple base class

## Architecture

```
scraparr/
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── core/     # Core functionality (config, security, db)
│   │   ├── scrapers/ # Base scraper framework
│   │   └── services/ # Business logic
│   ├── requirements.txt
│   └── main.py
├── frontend/         # React frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── scrapers/         # Custom scraper implementations
│   ├── example_api_scraper.py
│   └── example_web_scraper.py
├── docker/           # Docker configurations
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── postgres.Dockerfile
├── docker-compose.yml
└── docs/             # Additional documentation
```

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **Alembic**: Database migrations
- **APScheduler**: Advanced job scheduling
- **asyncpg**: Async PostgreSQL driver
- **httpx**: Async HTTP client for API scraping
- **BeautifulSoup4**: HTML parsing for web scraping
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI library
- **TypeScript**: Type safety
- **Material-UI (MUI)**: Component library
- **React Query**: Data fetching and caching
- **React Router**: Navigation
- **Axios**: HTTP client
- **date-fns**: Date utilities

### Database
- **PostgreSQL 15**: Relational database with schema isolation

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/depeter/scraparr.git
   cd scraparr
   ```

2. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

## Creating a Scraper

### API Scraper Example

```python
from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List

class MyAPIScraper(BaseScraper):
    scraper_type = ScraperType.API

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch data from API endpoint"""
        response = await self.http_client.get(
            "https://api.example.com/data",
            params=params
        )
        data = response.json()

        # Process and return data
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "value": item["value"]
            }
            for item in data["results"]
        ]
```

### Web Scraper Example

```python
from app.scrapers.base import BaseScraper, ScraperType
from bs4 import BeautifulSoup
from typing import Dict, Any, List

class MyWebScraper(BaseScraper):
    scraper_type = ScraperType.WEB

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape data from web page"""
        response = await self.http_client.get("https://example.com/page")
        soup = BeautifulSoup(response.content, 'html.parser')

        results = []
        for item in soup.select('.item-class'):
            results.append({
                "title": item.select_one('.title').text.strip(),
                "description": item.select_one('.desc').text.strip(),
                "url": item.select_one('a')['href']
            })

        return results
```

## Database Management

Each scraper can have its own PostgreSQL schema, allowing for different table structures per site.

### Schema Creation

When you create a scraper through the UI or API, Scraparr automatically:
1. Creates a new PostgreSQL schema named `scraper_{scraper_id}`
2. Sets up the schema with permissions
3. Allows your scraper to define custom tables

### Custom Tables

```python
from app.scrapers.base import BaseScraper
from sqlalchemy import Table, Column, Integer, String, DateTime

class MyCustomScraper(BaseScraper):
    def define_tables(self):
        """Define custom tables for this scraper's schema"""
        return [
            Table(
                'products',
                self.metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String(255)),
                Column('price', Integer),
                Column('scraped_at', DateTime)
            )
        ]
```

## Scheduling

Scraparr uses cron-like expressions for scheduling:

- `0 * * * *` - Every hour
- `0 0 * * *` - Daily at midnight
- `0 0 * * 0` - Weekly on Sunday
- `0 0 1 * *` - Monthly on the 1st

You can also run scrapers on-demand through the UI or API.

## API Endpoints

### Scrapers
- `GET /api/scrapers` - List all scrapers
- `POST /api/scrapers` - Create new scraper
- `GET /api/scrapers/{id}` - Get scraper details
- `PUT /api/scrapers/{id}` - Update scraper
- `DELETE /api/scrapers/{id}` - Delete scraper

### Jobs
- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create/schedule new job
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/run` - Run job immediately
- `DELETE /api/jobs/{id}` - Delete job

### Executions
- `GET /api/executions` - List job executions
- `GET /api/executions/{id}` - Get execution details
- `GET /api/executions/{id}/logs` - Get execution logs

## Configuration

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://scraparr:scraparr@localhost:5432/scraparr

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DEBUG=True

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive technical documentation for Claude Code
- **[SESSION_SUMMARY.md](SESSION_SUMMARY.md)** - Current project state and recent work
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference and cheat sheet

## Current State (2025-11-04)

- ✅ 29 weekly scheduled jobs for European countries
- ✅ Grid-based Park4Night scraper fully implemented
- ✅ Resume capability working
- ✅ Random delays (1-5s) for respectful API usage
- ✅ ~100,000+ camping locations expected after full collection
- ✅ Jobs running: UK, France, Italy currently scraping

Next scheduled run: Spain - Tuesday 1:00 AM UTC

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

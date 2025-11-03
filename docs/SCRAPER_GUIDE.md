# Scraper Development Guide

This guide will help you create custom scrapers for Scraparr.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Base Scraper Class](#base-scraper-class)
3. [API Scraper Example](#api-scraper-example)
4. [Web Scraper Example](#web-scraper-example)
5. [Custom Database Tables](#custom-database-tables)
6. [Hooks and Lifecycle](#hooks-and-lifecycle)
7. [Best Practices](#best-practices)

## Quick Start

1. Create a new Python file in the `scrapers/` directory
2. Import the base scraper class
3. Create your scraper class inheriting from `BaseScraper`
4. Implement the `scrape()` method
5. Register your scraper in the UI

## Base Scraper Class

All scrapers must inherit from `BaseScraper`:

```python
from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List

class MyCustomScraper(BaseScraper):
    scraper_type = ScraperType.API  # or ScraperType.WEB

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Your scraping logic here
        pass
```

### Available Attributes

- `self.scraper_id` - Database ID of the scraper
- `self.schema_name` - PostgreSQL schema name for this scraper's data
- `self.config` - Custom configuration dictionary
- `self.headers` - HTTP headers dictionary
- `self.http_client` - Async HTTP client (httpx.AsyncClient)
- `self.metadata` - SQLAlchemy metadata for custom tables
- `self.logger` - Python logger instance

### Available Methods

- `self.log(message, level='info')` - Log a message
- `self.parse_html(html, parser='html.parser')` - Parse HTML with BeautifulSoup
- `self.define_tables()` - Define custom database tables
- `self.before_scrape(params)` - Hook before scraping
- `self.after_scrape(results, params)` - Hook after scraping
- `self.on_error(error, params)` - Hook on error

## API Scraper Example

### Simple API Scraper

```python
from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List

class GitHubAPIScraperr(BaseScraper):
    scraper_type = ScraperType.API

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch GitHub repository info"""
        owner = params.get("owner", "octocat")
        repo = params.get("repo", "Hello-World")

        url = f"https://api.github.com/repos/{owner}/{repo}"
        self.log(f"Fetching repository: {owner}/{repo}")

        response = await self.http_client.get(url)
        response.raise_for_status()

        data = response.json()

        return [{
            "name": data["name"],
            "description": data["description"],
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "language": data["language"],
        }]
```

### API Scraper with Authentication

```python
class AuthenticatedAPIScraper(BaseScraper):
    scraper_type = ScraperType.API

    async def before_scrape(self, params: Dict[str, Any]) -> None:
        """Set up authentication"""
        api_key = self.config.get("api_key")
        if not api_key:
            raise ValueError("api_key not found in config")

        self.http_client.headers["Authorization"] = f"Bearer {api_key}"
        self.log("Authentication configured")

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch data from authenticated API"""
        response = await self.http_client.get(
            "https://api.example.com/protected-data"
        )
        response.raise_for_status()
        return response.json()
```

### Paginated API Scraper

```python
class PaginatedScraper(BaseScraper):
    scraper_type = ScraperType.API

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch all pages from paginated API"""
        base_url = "https://api.example.com/items"
        max_pages = params.get("max_pages", 10)
        all_results = []

        for page in range(1, max_pages + 1):
            self.log(f"Fetching page {page}")

            response = await self.http_client.get(
                base_url,
                params={"page": page, "per_page": 100}
            )
            response.raise_for_status()

            data = response.json()
            if not data:
                self.log("No more data")
                break

            all_results.extend(data)

        self.log(f"Total items: {len(all_results)}")
        return all_results
```

## Web Scraper Example

### Simple Web Scraper

```python
from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List

class HackerNewsScraper(BaseScraper):
    scraper_type = ScraperType.WEB

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape front page of Hacker News"""
        url = "https://news.ycombinator.com/"
        self.log(f"Scraping {url}")

        response = await self.http_client.get(url)
        response.raise_for_status()

        soup = await self.parse_html(response.text)

        stories = soup.select('.athing')
        results = []

        for story in stories:
            title_elem = story.select_one('.titleline > a')
            score_elem = story.find_next_sibling().select_one('.score')

            if title_elem:
                results.append({
                    "title": title_elem.text.strip(),
                    "url": title_elem['href'],
                    "score": score_elem.text if score_elem else "0 points"
                })

        self.log(f"Scraped {len(results)} stories")
        return results
```

### Multi-Page Web Scraper

```python
class EcommerceScraper(BaseScraper):
    scraper_type = ScraperType.WEB

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape products from multiple pages"""
        base_url = params.get("url", "https://example.com/products")
        max_pages = params.get("max_pages", 5)
        all_products = []

        for page_num in range(1, max_pages + 1):
            url = f"{base_url}?page={page_num}"
            self.log(f"Scraping page {page_num}")

            try:
                response = await self.http_client.get(url)
                response.raise_for_status()

                soup = await self.parse_html(response.text)
                products = soup.select('.product-card')

                for product in products:
                    all_products.append({
                        "name": product.select_one('.name').text.strip(),
                        "price": product.select_one('.price').text.strip(),
                        "url": product.select_one('a')['href']
                    })

            except Exception as e:
                self.log(f"Error on page {page_num}: {e}", level="warning")
                continue

        return all_products
```

## Custom Database Tables

You can define custom tables for your scraper's data:

```python
from sqlalchemy import Table, Column, Integer, String, DateTime, Float, func

class ProductScraper(BaseScraper):
    scraper_type = ScraperType.WEB

    def define_tables(self) -> List[Table]:
        """Define custom tables in scraper's schema"""
        return [
            Table(
                'products',
                self.metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('product_id', String(100), unique=True),
                Column('name', String(500)),
                Column('price', Float),
                Column('currency', String(10)),
                Column('in_stock', Boolean),
                Column('url', String(1000)),
                Column('scraped_at', DateTime, default=func.now()),
            ),
            Table(
                'prices_history',
                self.metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('product_id', String(100)),
                Column('price', Float),
                Column('recorded_at', DateTime, default=func.now()),
            )
        ]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Scraping logic here
        pass
```

The tables will be created automatically in the scraper's dedicated PostgreSQL schema.

## Hooks and Lifecycle

### before_scrape()

Called before scraping starts. Use for setup, authentication, etc.

```python
async def before_scrape(self, params: Dict[str, Any]) -> None:
    self.log("Setting up scraper")
    # Setup code here
```

### after_scrape()

Called after scraping completes successfully.

```python
async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
    self.log(f"Finished scraping {len(results)} items")
    # Cleanup or post-processing here
```

### on_error()

Called when scraping fails.

```python
async def on_error(self, error: Exception, params: Dict[str, Any]) -> None:
    self.log(f"Scraping failed: {str(error)}", level="error")
    # Error handling here
```

## Best Practices

### 1. Always Use Logging

```python
self.log("Starting scrape")
self.log(f"Processing {len(items)} items")
self.log("Error occurred", level="error")
```

### 2. Handle Errors Gracefully

```python
try:
    response = await self.http_client.get(url)
    response.raise_for_status()
except httpx.HTTPError as e:
    self.log(f"HTTP error: {e}", level="error")
    raise
```

### 3. Respect Rate Limits

```python
import asyncio

async def scrape(self, params):
    for url in urls:
        await self.http_client.get(url)
        await asyncio.sleep(1)  # Wait 1 second between requests
```

### 4. Use Configuration

Store API keys, base URLs, etc. in the scraper's config:

```python
async def scrape(self, params):
    base_url = self.config.get("base_url", "https://default.com")
    api_key = self.config.get("api_key")
```

### 5. Validate Parameters

```python
async def scrape(self, params):
    url = params.get("url")
    if not url:
        raise ValueError("url parameter is required")
```

### 6. Return Structured Data

Always return a list of dictionaries:

```python
return [
    {"id": 1, "name": "Item 1"},
    {"id": 2, "name": "Item 2"},
]
```

### 7. Use Type Hints

```python
async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    ...
```

## Testing Your Scraper

1. Create the scraper file in `scrapers/`
2. Register it in the Scraparr UI:
   - Module path: `scrapers.my_scraper`
   - Class name: `MyScraperClass`
3. Click "Validate" to check if it loads correctly
4. Run it manually with test parameters
5. Check execution logs for errors

## Example: Complete Real-World Scraper

```python
from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List
import asyncio

class ComprehensiveScraper(BaseScraper):
    """Complete example with all features"""

    scraper_type = ScraperType.WEB

    async def before_scrape(self, params: Dict[str, Any]) -> None:
        """Validate configuration"""
        if not self.config.get("base_url"):
            raise ValueError("base_url not configured")
        self.log("Scraper initialized")

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Main scraping logic"""
        base_url = self.config["base_url"]
        max_pages = params.get("max_pages", 3)
        results = []

        for page in range(1, max_pages + 1):
            self.log(f"Processing page {page}")

            try:
                # Fetch page
                response = await self.http_client.get(
                    f"{base_url}/page/{page}"
                )
                response.raise_for_status()

                # Parse HTML
                soup = await self.parse_html(response.text)

                # Extract data
                items = soup.select('.item')
                for item in items:
                    results.append({
                        "title": item.select_one('.title').text.strip(),
                        "url": item.select_one('a')['href'],
                        "page": page,
                    })

                # Rate limiting
                await asyncio.sleep(1)

            except Exception as e:
                self.log(f"Error on page {page}: {e}", level="warning")
                continue

        self.log(f"Scraped {len(results)} total items")
        return results

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """Log completion"""
        self.log(f"Scraping completed successfully")

    async def on_error(self, error: Exception, params: Dict[str, Any]) -> None:
        """Handle errors"""
        self.log(f"Scraping failed: {str(error)}", level="error")
```

## Need Help?

- Check the example scrapers in `scrapers/example_api_scraper.py` and `scrapers/example_web_scraper.py`
- Review execution logs for debugging
- Ensure your scraper follows the patterns in this guide

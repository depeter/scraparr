# UiTinVlaanderen Scraper Implementation Plan

## Overview

**Target:** UiTinVlaanderen.be (Belgium/Flanders)
**Priority:** Tier 1 - HIGHEST
**Estimated Implementation:** 3-5 days
**Difficulty:** LOW-MEDIUM

---

## Phase 1: Investigation (Day 1)

### 1.1 Check for Official API
**Action:** Research if UiTdatabank has public API access

**URLs to investigate:**
- https://www.uitinvlaanderen.be/
- https://www.uitdatabank.be/ (successor of Cultuurdatabank)
- Look for developer documentation
- Check robots.txt and sitemap.xml

**Expected outcomes:**
- ✅ **Best case:** Public API with documentation
- ⚠️ **Medium case:** Partner API requiring registration
- ❌ **Worst case:** No API, must scrape HTML

**Investigation script:**
```python
# scrapers/investigations/uitinvlaanderen_api_check.py
import requests
from bs4 import BeautifulSoup

def check_api_availability():
    """Check if UiTdatabank has public API"""

    # Check main site
    urls_to_check = [
        'https://www.uitinvlaanderen.be/',
        'https://www.uitdatabank.be/',
        'https://documentatie.uitdatabank.be/',
        'https://www.uitinvlaanderen.be/api',
        'https://docs.publiq.be/',
    ]

    for url in urls_to_check:
        try:
            response = requests.get(url, timeout=10)
            print(f"\n{url}: {response.status_code}")

            # Look for API keywords
            keywords = ['api', 'developer', 'documentation', 'endpoints', 'json', 'rest']
            content = response.text.lower()

            found_keywords = [kw for kw in keywords if kw in content]
            if found_keywords:
                print(f"  Found keywords: {', '.join(found_keywords)}")

        except Exception as e:
            print(f"{url}: ERROR - {e}")

    # Check robots.txt
    try:
        robots_url = 'https://www.uitinvlaanderen.be/robots.txt'
        response = requests.get(robots_url, timeout=10)
        print(f"\n--- robots.txt ---")
        print(response.text)
    except:
        pass

    # Check sitemap
    try:
        sitemap_url = 'https://www.uitinvlaanderen.be/sitemap.xml'
        response = requests.get(sitemap_url, timeout=10)
        print(f"\n--- sitemap.xml (first 1000 chars) ---")
        print(response.text[:1000])
    except:
        pass

if __name__ == '__main__':
    check_api_availability()
```

### 1.2 Analyze Page Structure
**Action:** Understand how events are listed and detailed

**Questions to answer:**
1. How are events listed? (Grid, list, infinite scroll?)
2. What's the pagination structure?
3. Are there filters? (Date, location, category)
4. Is data rendered client-side (JavaScript) or server-side?
5. What's the URL structure for event details?

**Exploration script:**
```python
# scrapers/investigations/uitinvlaanderen_structure.py
import requests
from bs4 import BeautifulSoup
import json

def analyze_page_structure():
    """Analyze UiTinVlaanderen page structure"""

    base_url = 'https://www.uitinvlaanderen.be/agenda'

    print("=== Fetching main agenda page ===")
    response = requests.get(base_url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    })

    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")

    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for JSON-LD structured data
    print("\n=== Looking for JSON-LD structured data ===")
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            print(f"\nJSON-LD block {i+1}:")
            print(json.dumps(data, indent=2)[:500])
        except:
            pass

    # Look for event containers
    print("\n=== Looking for event containers ===")
    possible_selectors = [
        ('div.event', 'div with class "event"'),
        ('article', 'article tags'),
        ('[data-event-id]', 'elements with event ID'),
        ('.agenda-item', 'agenda items'),
        ('.event-card', 'event cards'),
    ]

    for selector, description in possible_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"Found {len(elements)} x {description}")
            print(f"  First element classes: {elements[0].get('class')}")

    # Check for API calls in page source
    print("\n=== Checking for API endpoints in HTML ===")
    api_patterns = ['/api/', '/rest/', '/v1/', '/v2/', '/v3/', 'api.', 'graphql']
    for pattern in api_patterns:
        if pattern in response.text:
            print(f"  Found '{pattern}' in page source - possible API!")

    # Save full HTML for manual inspection
    with open('/tmp/uitinvlaanderen_page.html', 'w') as f:
        f.write(response.text)
    print("\n✓ Saved full HTML to /tmp/uitinvlaanderen_page.html")

if __name__ == '__main__':
    analyze_page_structure()
```

### 1.3 Network Analysis
**Action:** Use browser DevTools to see actual network requests

**Manual steps:**
1. Open https://www.uitinvlaanderen.be/agenda in Chrome/Firefox
2. Open DevTools (F12) → Network tab
3. Filter by XHR/Fetch
4. Scroll through events, change filters
5. Document any API calls you see

**Look for:**
- API endpoints (likely JSON responses)
- GraphQL queries
- AJAX pagination requests
- Filter parameter structures

---

## Phase 2: Implementation Strategy (Day 2)

### Decision Tree

#### ✅ If API Exists (Best Case)

**Implementation: `scrapers/uitinvlaanderen_api_scraper.py`**

```python
"""
UiTinVlaanderen API Scraper

API-based scraper for Belgian/Flemish events from UiTdatabank.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class UiTinVlaanderenAPIScraper:
    """Scraper for UiTinVlaanderen using official API"""

    BASE_URL = "https://api.uitdatabank.be/v3/"  # Example, update after investigation

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'

        self.session.headers['User-Agent'] = 'Scraparr/1.0 (Event Aggregator)'

    def search_events(
        self,
        start_date: datetime,
        end_date: datetime,
        location: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Search for events using API

        Args:
            start_date: Start of date range
            end_date: End of date range
            location: City/region filter
            limit: Results per page
            offset: Pagination offset

        Returns:
            List of event dictionaries
        """

        params = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'limit': limit,
            'offset': offset,
        }

        if location:
            params['location'] = location

        response = self.session.get(
            f'{self.BASE_URL}/events',
            params=params,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        return data.get('items', [])

    def get_event_details(self, event_id: str) -> Dict:
        """Get detailed information for a specific event"""

        response = self.session.get(
            f'{self.BASE_URL}/events/{event_id}',
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    def scrape_all_events(
        self,
        days_ahead: int = 90,
        batch_size: int = 50
    ) -> List[Dict]:
        """
        Scrape all events for the next N days

        Args:
            days_ahead: Number of days to look ahead
            batch_size: Events per request

        Returns:
            List of all events
        """

        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)

        all_events = []
        offset = 0

        logger.info(f"Scraping events from {start_date.date()} to {end_date.date()}")

        while True:
            logger.info(f"Fetching batch at offset {offset}")

            events = self.search_events(
                start_date=start_date,
                end_date=end_date,
                limit=batch_size,
                offset=offset
            )

            if not events:
                break

            all_events.extend(events)
            offset += batch_size

            logger.info(f"Retrieved {len(events)} events (total: {len(all_events)})")

            # Be polite - rate limiting
            import time
            time.sleep(1)

        logger.info(f"✓ Scraped {len(all_events)} events total")
        return all_events

    def normalize_event(self, raw_event: Dict) -> Dict:
        """
        Normalize API response to Scraparr standard format

        Returns:
            Standardized event dictionary
        """

        # TODO: Adjust field mapping based on actual API response
        return {
            'source': 'uitinvlaanderen',
            'source_id': raw_event.get('@id'),
            'name': raw_event.get('name', {}).get('nl'),
            'description': raw_event.get('description', {}).get('nl'),
            'start_date': raw_event.get('startDate'),
            'end_date': raw_event.get('endDate'),
            'venue_name': raw_event.get('location', {}).get('name', {}).get('nl'),
            'address': self._extract_address(raw_event.get('location', {})),
            'city': raw_event.get('location', {}).get('address', {}).get('nl', {}).get('addressLocality'),
            'country': 'BE',
            'latitude': raw_event.get('location', {}).get('geo', {}).get('latitude'),
            'longitude': raw_event.get('location', {}).get('geo', {}).get('longitude'),
            'categories': [term.get('label') for term in raw_event.get('terms', [])],
            'price_min': self._extract_price_min(raw_event.get('priceInfo', [])),
            'price_max': self._extract_price_max(raw_event.get('priceInfo', [])),
            'url': raw_event.get('url'),
            'image_url': raw_event.get('image'),
            'organizer': raw_event.get('organizer', {}).get('name', {}).get('nl'),
            'scraped_at': datetime.utcnow().isoformat(),
        }

    def _extract_address(self, location: Dict) -> str:
        """Extract formatted address from location object"""
        address = location.get('address', {}).get('nl', {})
        parts = [
            address.get('streetAddress'),
            address.get('postalCode'),
            address.get('addressLocality'),
        ]
        return ', '.join(filter(None, parts))

    def _extract_price_min(self, price_info: List[Dict]) -> Optional[float]:
        """Extract minimum price from price info"""
        if not price_info:
            return None
        prices = [p.get('price') for p in price_info if p.get('price') is not None]
        return min(prices) if prices else None

    def _extract_price_max(self, price_info: List[Dict]) -> Optional[float]:
        """Extract maximum price from price info"""
        if not price_info:
            return None
        prices = [p.get('price') for p in price_info if p.get('price') is not None]
        return max(prices) if prices else None


# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    scraper = UiTinVlaanderenAPIScraper()

    # Scrape next 30 days
    events = scraper.scrape_all_events(days_ahead=30)

    # Normalize to standard format
    normalized_events = [scraper.normalize_event(event) for event in events]

    print(f"\n✓ Scraped and normalized {len(normalized_events)} events")

    # Show sample
    if normalized_events:
        import json
        print("\nSample event:")
        print(json.dumps(normalized_events[0], indent=2, ensure_ascii=False))
```

#### ⚠️ If No API (HTML Scraping Required)

**Implementation: `scrapers/uitinvlaanderen_html_scraper.py`**

```python
"""
UiTinVlaanderen HTML Scraper

HTML-based scraper for Belgian/Flemish events when API is not available.
Uses Playwright for JavaScript rendering if needed.
"""

import asyncio
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class UiTinVlaanderenHTMLScraper:
    """Scraper for UiTinVlaanderen using HTML parsing"""

    BASE_URL = "https://www.uitinvlaanderen.be"
    AGENDA_URL = f"{BASE_URL}/agenda"

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def scrape_event_list(self, page_num: int = 1) -> List[str]:
        """
        Scrape event URLs from listing page

        Args:
            page_num: Page number to scrape

        Returns:
            List of event detail URLs
        """

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            # Navigate to agenda
            url = f"{self.AGENDA_URL}?page={page_num}"
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until='networkidle')

            # Wait for events to load
            await page.wait_for_selector('[data-event-id], .event-card, article', timeout=10000)

            # Extract event URLs
            event_urls = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/agenda/e/"]'));
                return links.map(link => link.href);
            }''')

            await browser.close()

            # Deduplicate
            event_urls = list(set(event_urls))
            logger.info(f"Found {len(event_urls)} event URLs on page {page_num}")

            return event_urls

    async def scrape_event_details(self, url: str) -> Dict:
        """
        Scrape detailed information from event page

        Args:
            url: Event detail page URL

        Returns:
            Event data dictionary
        """

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            logger.info(f"Scraping event: {url}")
            await page.goto(url, wait_until='networkidle')

            # Extract event data
            event_data = await page.evaluate('''() => {
                // Extract JSON-LD if available
                const jsonLd = document.querySelector('script[type="application/ld+json"]');
                if (jsonLd) {
                    try {
                        return JSON.parse(jsonLd.textContent);
                    } catch (e) {}
                }

                // Fallback to HTML parsing
                return {
                    name: document.querySelector('h1')?.textContent?.trim(),
                    description: document.querySelector('.description, .event-description')?.textContent?.trim(),
                    // Add more selectors based on actual page structure
                };
            }''')

            # Get full HTML for backup parsing
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            await browser.close()

            # Enhance with additional parsing if needed
            event_data['url'] = url
            event_data['scraped_at'] = datetime.utcnow().isoformat()

            return event_data

    async def scrape_all_events(self, max_pages: int = 10) -> List[Dict]:
        """
        Scrape all events from multiple pages

        Args:
            max_pages: Maximum number of listing pages to scrape

        Returns:
            List of all event data
        """

        all_event_urls = []

        # Scrape listing pages
        for page_num in range(1, max_pages + 1):
            urls = await self.scrape_event_list(page_num)

            if not urls:
                logger.info(f"No more events found, stopping at page {page_num}")
                break

            all_event_urls.extend(urls)

            # Be polite
            await asyncio.sleep(2)

        logger.info(f"Found {len(all_event_urls)} total event URLs")

        # Scrape event details
        all_events = []

        for i, url in enumerate(all_event_urls, 1):
            logger.info(f"Scraping event {i}/{len(all_event_urls)}")

            try:
                event_data = await self.scrape_event_details(url)
                all_events.append(event_data)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")

            # Rate limiting
            await asyncio.sleep(3)

        logger.info(f"✓ Successfully scraped {len(all_events)} events")
        return all_events


# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    scraper = UiTinVlaanderenHTMLScraper(headless=True)

    # Run async scraper
    events = asyncio.run(scraper.scrape_all_events(max_pages=3))

    print(f"\n✓ Scraped {len(events)} events")

    if events:
        import json
        print("\nSample event:")
        print(json.dumps(events[0], indent=2, ensure_ascii=False))
```

---

## Phase 3: Testing & Validation (Day 3)

### 3.1 Unit Tests

```python
# tests/test_uitinvlaanderen_scraper.py
import pytest
from datetime import datetime, timedelta
from scrapers.uitinvlaanderen_api_scraper import UiTinVlaanderenAPIScraper

@pytest.fixture
def scraper():
    return UiTinVlaanderenAPIScraper()

def test_scraper_initialization(scraper):
    """Test scraper initializes correctly"""
    assert scraper.BASE_URL
    assert scraper.session

def test_search_events(scraper):
    """Test event search returns data"""
    start = datetime.now()
    end = start + timedelta(days=7)

    events = scraper.search_events(start, end, limit=10)

    assert isinstance(events, list)
    if events:
        assert 'name' in events[0] or '@id' in events[0]

def test_event_normalization(scraper):
    """Test event data normalization"""

    raw_event = {
        '@id': 'test-123',
        'name': {'nl': 'Test Event'},
        'startDate': '2025-01-01T20:00:00',
        'location': {
            'name': {'nl': 'Test Venue'},
            'address': {
                'nl': {
                    'streetAddress': 'Test Street 1',
                    'postalCode': '1000',
                    'addressLocality': 'Brussels'
                }
            },
            'geo': {'latitude': 50.8503, 'longitude': 4.3517}
        }
    }

    normalized = scraper.normalize_event(raw_event)

    assert normalized['source'] == 'uitinvlaanderen'
    assert normalized['source_id'] == 'test-123'
    assert normalized['name'] == 'Test Event'
    assert normalized['city'] == 'Brussels'
    assert normalized['country'] == 'BE'

def test_rate_limiting(scraper):
    """Test scraper respects rate limits"""
    import time

    start = datetime.now()
    end = start + timedelta(days=1)

    start_time = time.time()
    scraper.search_events(start, end, limit=5)
    scraper.search_events(start, end, limit=5)
    elapsed = time.time() - start_time

    # Should take at least 1 second due to sleep(1)
    assert elapsed >= 1.0
```

### 3.2 Integration Tests

```python
# tests/integration/test_uitinvlaanderen_integration.py
import pytest
from scrapers.uitinvlaanderen_api_scraper import UiTinVlaanderenAPIScraper
from database import Database  # Your database module

@pytest.fixture
def scraper():
    return UiTinVlaanderenAPIScraper()

@pytest.fixture
def db():
    # Use test database
    db = Database('postgresql://test:test@localhost/scraparr_test')
    yield db
    db.cleanup()

def test_full_scrape_and_save(scraper, db):
    """Test complete scrape → normalize → save pipeline"""

    # Scrape events
    events = scraper.scrape_all_events(days_ahead=7)
    assert len(events) > 0

    # Normalize
    normalized = [scraper.normalize_event(e) for e in events]

    # Save to database
    saved_count = db.save_events(normalized)
    assert saved_count > 0

    # Verify in database
    retrieved = db.get_events(source='uitinvlaanderen', limit=10)
    assert len(retrieved) > 0
    assert retrieved[0]['source'] == 'uitinvlaanderen'

def test_duplicate_handling(scraper, db):
    """Test scraper handles duplicates correctly"""

    events = scraper.scrape_all_events(days_ahead=7)
    normalized = [scraper.normalize_event(e) for e in events[:5]]

    # Save twice
    count1 = db.save_events(normalized)
    count2 = db.save_events(normalized)  # Should upsert, not duplicate

    # Verify no duplicates
    total = db.count_events(source='uitinvlaanderen')
    assert total == count1
```

### 3.3 Data Quality Checks

```python
# tests/test_data_quality.py
def test_event_data_quality(scraper):
    """Validate quality of scraped data"""

    events = scraper.scrape_all_events(days_ahead=7)
    normalized = [scraper.normalize_event(e) for e in events]

    for event in normalized[:20]:  # Check first 20
        # Required fields
        assert event.get('name'), "Event must have name"
        assert event.get('source_id'), "Event must have source_id"
        assert event.get('start_date'), "Event must have start_date"
        assert event.get('city'), "Event must have city"

        # Valid dates
        try:
            start = datetime.fromisoformat(event['start_date'])
            assert start > datetime(2020, 1, 1), "Date seems too old"
        except:
            pytest.fail(f"Invalid start_date format: {event['start_date']}")

        # Valid coordinates if present
        if event.get('latitude'):
            lat = float(event['latitude'])
            assert 49 <= lat <= 52, "Latitude outside Belgium range"

        if event.get('longitude'):
            lon = float(event['longitude'])
            assert 2 <= lon <= 7, "Longitude outside Belgium range"

        # URL validity
        if event.get('url'):
            assert event['url'].startswith('http'), "Invalid URL"
```

---

## Phase 4: Production Deployment (Day 4-5)

### 4.1 Scheduler Integration

```python
# scrapers/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scrapers.uitinvlaanderen_api_scraper import UiTinVlaanderenAPIScraper
from database import Database
import logging

logger = logging.getLogger(__name__)

class ScraperScheduler:
    """Scheduler for running scrapers periodically"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db = Database()
        self.scrapers = {
            'uitinvlaanderen': UiTinVlaanderenAPIScraper()
        }

    def run_uitinvlaanderen_scrape(self):
        """Run UiTinVlaanderen scraper job"""

        logger.info("Starting UiTinVlaanderen scrape job")

        try:
            scraper = self.scrapers['uitinvlaanderen']

            # Scrape events
            events = scraper.scrape_all_events(days_ahead=90)
            logger.info(f"Scraped {len(events)} events")

            # Normalize
            normalized = [scraper.normalize_event(e) for e in events]

            # Save to database
            saved = self.db.save_events(normalized)
            logger.info(f"Saved {saved} events to database")

            # Log statistics
            self.db.log_scrape_run(
                source='uitinvlaanderen',
                events_found=len(events),
                events_saved=saved,
                status='success'
            )

        except Exception as e:
            logger.error(f"UiTinVlaanderen scrape failed: {e}", exc_info=True)
            self.db.log_scrape_run(
                source='uitinvlaanderen',
                events_found=0,
                events_saved=0,
                status='failed',
                error_message=str(e)
            )

    def start(self):
        """Start scheduler with configured jobs"""

        # Run UiTinVlaanderen every day at 3 AM
        self.scheduler.add_job(
            self.run_uitinvlaanderen_scrape,
            'cron',
            hour=3,
            minute=0,
            id='uitinvlaanderen_daily'
        )

        logger.info("Scheduler started with jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.id}: {job.next_run_time}")

        self.scheduler.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    scheduler = ScraperScheduler()
    scheduler.start()

    # Keep running
    import asyncio
    asyncio.get_event_loop().run_forever()
```

### 4.2 Monitoring & Alerts

```python
# monitoring/scraper_health.py
from database import Database
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ScraperHealthMonitor:
    """Monitor scraper health and send alerts"""

    def __init__(self, db: Database):
        self.db = db

    def check_recent_scrapes(self, hours: int = 24):
        """Check if scrapers have run recently"""

        cutoff = datetime.now() - timedelta(hours=hours)

        sources = ['uitinvlaanderen']

        for source in sources:
            last_run = self.db.get_last_scrape_run(source)

            if not last_run:
                logger.warning(f"⚠️  {source}: No scrape runs found!")
                self.send_alert(f"{source} has never run")
                continue

            if last_run['timestamp'] < cutoff:
                hours_ago = (datetime.now() - last_run['timestamp']).total_seconds() / 3600
                logger.warning(f"⚠️  {source}: Last run was {hours_ago:.1f} hours ago")
                self.send_alert(f"{source} hasn't run in {hours_ago:.1f} hours")

            if last_run['status'] == 'failed':
                logger.error(f"❌ {source}: Last run FAILED - {last_run.get('error_message')}")
                self.send_alert(f"{source} last run failed: {last_run.get('error_message')}")

            if last_run['events_saved'] == 0:
                logger.warning(f"⚠️  {source}: Last run saved 0 events")
                self.send_alert(f"{source} saved 0 events on last run")

    def send_alert(self, message: str):
        """Send alert via configured channels"""
        logger.error(f"ALERT: {message}")

        # TODO: Integrate with alerting system
        # - Email
        # - Slack
        # - Discord
        # - PagerDuty
        pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    db = Database()
    monitor = ScraperHealthMonitor(db)

    monitor.check_recent_scrapes(hours=26)
```

### 4.3 Docker Deployment

```dockerfile
# docker/Dockerfile.scrapers
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy scraper code
COPY scrapers/ ./scrapers/
COPY database/ ./database/
COPY monitoring/ ./monitoring/

# Run scheduler
CMD ["python", "-u", "scrapers/scheduler.py"]
```

```yaml
# docker-compose.yml (add to existing)
services:
  scrapers:
    build:
      context: .
      dockerfile: docker/Dockerfile.scrapers
    environment:
      - DATABASE_URL=postgresql://scraparr:${DB_PASSWORD}@db:5432/scraparr
      - LOG_LEVEL=INFO
    depends_on:
      - db
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

---

## Success Metrics

### Key Performance Indicators (KPIs)

**Data Quality:**
- ✅ 95%+ events have valid names
- ✅ 90%+ events have valid dates
- ✅ 80%+ events have venue information
- ✅ 70%+ events have coordinates
- ✅ <5% duplicate events

**Coverage:**
- ✅ Scrape events from next 90 days
- ✅ Cover all Belgian regions
- ✅ Include all event categories

**Reliability:**
- ✅ Scraper runs daily without failures
- ✅ <1% error rate on individual events
- ✅ Recovery from temporary failures
- ✅ No data loss

**Performance:**
- ✅ Complete scrape in <30 minutes
- ✅ Rate limit respected (no bans)
- ✅ Database updates efficiently

---

## Troubleshooting Guide

### Common Issues

**Issue: API returns 401 Unauthorized**
- **Cause:** API key required or invalid
- **Solution:** Register for API access or implement OAuth flow

**Issue: No events returned**
- **Cause:** Date range filters incorrect
- **Solution:** Check date format (ISO 8601), verify timezone

**Issue: HTML structure changed**
- **Cause:** Website redesign
- **Solution:** Update selectors in HTML scraper, add version detection

**Issue: Rate limited (429 errors)**
- **Cause:** Too many requests
- **Solution:** Increase sleep time between requests, implement exponential backoff

**Issue: Playwright timeout**
- **Cause:** Slow page load or incorrect selector
- **Solution:** Increase timeout, verify selectors in browser DevTools

**Issue: Duplicate events in database**
- **Cause:** source_id not unique
- **Solution:** Fix source_id extraction, add database constraints

---

## Next Steps After Success

Once UiTinVlaanderen scraper is working:

1. **Document learnings** - Create scraper template based on this implementation
2. **Extract common patterns** - Build base scraper class
3. **Move to next platform** - Implement Ticketmaster.co.uk (Tier 1)
4. **Build scraper framework** - Standardize error handling, retry logic, monitoring
5. **Create scraper dashboard** - Visualize scraping status, data quality metrics

---

## Estimated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Investigation | 1 day | API documentation OR HTML structure analysis |
| Implementation | 1-2 days | Working scraper (API or HTML version) |
| Testing | 1 day | Unit tests, integration tests, data validation |
| Deployment | 1 day | Scheduled job, monitoring, alerts |
| Documentation | 0.5 days | Code comments, usage guide, troubleshooting |

**Total: 4.5-5.5 days**

---

## Questions to Answer During Investigation

1. ✅ Does UiTdatabank have a public API?
2. ✅ If API exists, is authentication required?
3. ✅ What's the rate limit policy?
4. ✅ Is data available in structured format (JSON-LD)?
5. ✅ How are events categorized?
6. ✅ What date range can we query?
7. ✅ Are there regional filters available?
8. ✅ How often should we scrape (daily, weekly)?
9. ✅ What's the average event volume?
10. ✅ Are there any terms of service restrictions?

---

**Priority: START HERE** 🎯

This is your blueprint for the first scraper. Begin with Phase 1 investigation tomorrow!

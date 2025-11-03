"""
Example API scraper

This scraper demonstrates how to interact with a REST API
"""
import sys
sys.path.insert(0, '/app/backend')

from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List


class ExampleAPIScraper(BaseScraper):
    """Example scraper for REST API interaction"""

    scraper_type = ScraperType.API

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch data from a REST API

        Expected params:
            - url: API endpoint URL
            - query_params: Optional query parameters
        """
        url = params.get("url", "https://jsonplaceholder.typicode.com/posts")
        query_params = params.get("query_params", {})

        self.log(f"Fetching data from {url}")

        try:
            response = await self.http_client.get(url, params=query_params)
            response.raise_for_status()

            data = response.json()
            self.log(f"Successfully fetched {len(data)} items")

            # Process and transform data as needed
            results = []
            for item in data:
                results.append({
                    "id": item.get("id"),
                    "user_id": item.get("userId"),
                    "title": item.get("title"),
                    "body": item.get("body"),
                })

            return results

        except Exception as e:
            self.log(f"Error fetching data: {str(e)}", level="error")
            raise


# Example with authentication
class AuthenticatedAPIScraper(BaseScraper):
    """Example scraper with API authentication"""

    scraper_type = ScraperType.API

    async def before_scrape(self, params: Dict[str, Any]) -> None:
        """Set up authentication before scraping"""
        api_key = self.config.get("api_key")
        if api_key:
            self.http_client.headers["Authorization"] = f"Bearer {api_key}"
            self.log("Authentication configured")

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch authenticated API data

        Expected params:
            - endpoint: API endpoint path
        """
        base_url = self.config.get("base_url", "https://api.example.com")
        endpoint = params.get("endpoint", "/data")

        url = f"{base_url}{endpoint}"
        self.log(f"Fetching authenticated data from {url}")

        response = await self.http_client.get(url)
        response.raise_for_status()

        data = response.json()
        self.log(f"Successfully fetched {len(data)} items")

        return data


# Example with pagination
class PaginatedAPIScraper(BaseScraper):
    """Example scraper with pagination support"""

    scraper_type = ScraperType.API

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch paginated API data

        Expected params:
            - url: Base API URL
            - max_pages: Maximum number of pages to fetch (default: 10)
        """
        base_url = params.get("url", "https://api.example.com/items")
        max_pages = params.get("max_pages", 10)

        all_results = []
        page = 1

        while page <= max_pages:
            self.log(f"Fetching page {page}/{max_pages}")

            response = await self.http_client.get(
                base_url,
                params={"page": page, "per_page": 100}
            )
            response.raise_for_status()

            data = response.json()

            if not data:
                self.log("No more data available")
                break

            all_results.extend(data)
            page += 1

        self.log(f"Total items fetched: {len(all_results)}")
        return all_results

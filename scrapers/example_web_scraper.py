"""
Example web scraper

This scraper demonstrates how to scrape data from HTML web pages
"""
import sys
sys.path.insert(0, '/app/backend')

from app.scrapers.base import BaseScraper, ScraperType
from typing import Dict, Any, List
from sqlalchemy import Table, Column, Integer, String, DateTime, func


class ExampleWebScraper(BaseScraper):
    """Example scraper for HTML web pages"""

    scraper_type = ScraperType.WEB

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape data from an HTML page

        Expected params:
            - url: Web page URL
            - selector: CSS selector for items (default: '.item')
        """
        url = params.get("url", "https://example.com")
        selector = params.get("selector", ".item")

        self.log(f"Scraping page: {url}")

        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            soup = await self.parse_html(response.text)
            self.log("Page loaded and parsed successfully")

            items = soup.select(selector)
            self.log(f"Found {len(items)} items with selector '{selector}'")

            results = []
            for idx, item in enumerate(items, 1):
                title = item.select_one('.title')
                description = item.select_one('.description')
                link = item.select_one('a')

                result = {
                    "position": idx,
                    "title": title.text.strip() if title else None,
                    "description": description.text.strip() if description else None,
                    "url": link['href'] if link and link.has_attr('href') else None,
                }
                results.append(result)

            self.log(f"Successfully scraped {len(results)} items")
            return results

        except Exception as e:
            self.log(f"Error scraping page: {str(e)}", level="error")
            raise


class MultiPageWebScraper(BaseScraper):
    """Example scraper for multiple pages"""

    scraper_type = ScraperType.WEB

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape data from multiple pages

        Expected params:
            - base_url: Base URL pattern (e.g., https://example.com/page/{page})
            - start_page: Starting page number (default: 1)
            - end_page: Ending page number (default: 5)
        """
        base_url = params.get("base_url")
        start_page = params.get("start_page", 1)
        end_page = params.get("end_page", 5)

        if not base_url:
            raise ValueError("base_url parameter is required")

        all_results = []

        for page_num in range(start_page, end_page + 1):
            url = base_url.format(page=page_num)
            self.log(f"Scraping page {page_num}: {url}")

            try:
                response = await self.http_client.get(url)
                response.raise_for_status()

                soup = await self.parse_html(response.text)

                # Example: extract article titles and links
                articles = soup.select('article')

                for article in articles:
                    title_elem = article.select_one('h2')
                    link_elem = article.select_one('a')

                    if title_elem and link_elem:
                        all_results.append({
                            "page": page_num,
                            "title": title_elem.text.strip(),
                            "url": link_elem.get('href'),
                        })

            except Exception as e:
                self.log(f"Error on page {page_num}: {str(e)}", level="warning")
                continue

        self.log(f"Total items scraped: {len(all_results)}")
        return all_results


class ProductScraper(BaseScraper):
    """Example scraper for e-commerce products with custom table"""

    scraper_type = ScraperType.WEB

    def define_tables(self) -> List[Table]:
        """Define custom product table"""
        return [
            Table(
                'products',
                self.metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('product_id', String(100), unique=True),
                Column('name', String(500)),
                Column('price', String(50)),
                Column('currency', String(10)),
                Column('availability', String(50)),
                Column('url', String(1000)),
                Column('image_url', String(1000)),
                Column('scraped_at', DateTime, default=func.now()),
            )
        ]

    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape product information

        Expected params:
            - url: Product listing page URL
        """
        url = params.get("url")
        if not url:
            raise ValueError("url parameter is required")

        self.log(f"Scraping products from: {url}")

        response = await self.http_client.get(url)
        response.raise_for_status()

        soup = await self.parse_html(response.text)

        products = soup.select('.product-item')
        self.log(f"Found {len(products)} products")

        results = []
        for product in products:
            product_data = {
                "product_id": product.get('data-product-id'),
                "name": self._extract_text(product, '.product-name'),
                "price": self._extract_text(product, '.price'),
                "currency": self._extract_text(product, '.currency', default='USD'),
                "availability": self._extract_text(product, '.availability'),
                "url": self._extract_attr(product, 'a', 'href'),
                "image_url": self._extract_attr(product, 'img', 'src'),
            }
            results.append(product_data)

        self.log(f"Successfully scraped {len(results)} products")
        return results

    def _extract_text(self, parent, selector, default=None):
        """Helper to extract text from element"""
        elem = parent.select_one(selector)
        return elem.text.strip() if elem else default

    def _extract_attr(self, parent, selector, attr, default=None):
        """Helper to extract attribute from element"""
        elem = parent.select_one(selector)
        return elem.get(attr) if elem else default

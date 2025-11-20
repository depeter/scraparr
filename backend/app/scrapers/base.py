"""Base scraper class for all custom scrapers"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import MetaData, Table
from datetime import datetime
import logging


class ScraperType(str, Enum):
    """Scraper types"""
    API = "api"
    WEB = "web"


class BaseScraper(ABC):
    """
    Base scraper class that all custom scrapers should inherit from

    Example usage:
        class MyAPIScraper(BaseScraper):
            scraper_type = ScraperType.API

            async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
                response = await self.http_client.get("https://api.example.com/data")
                return response.json()
    """

    scraper_type: ScraperType = ScraperType.WEB

    def __init__(
        self,
        scraper_id: int,
        schema_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        execution_id: Optional[int] = None,
    ):
        """
        Initialize scraper

        Args:
            scraper_id: Database ID of the scraper
            schema_name: PostgreSQL schema name for this scraper's data
            config: Custom configuration for the scraper
            headers: HTTP headers to use
            execution_id: Execution ID for progress tracking
        """
        self.scraper_id = scraper_id
        self.schema_name = schema_name
        self.config = config or {}
        self.headers = headers or {}
        self.execution_id = execution_id
        self.logger = logging.getLogger(f"scraper.{scraper_id}")

        # HTTP client for making requests
        default_headers = {
            "User-Agent": "Scraparr/1.0",
            **self.headers
        }
        self.http_client = httpx.AsyncClient(
            headers=default_headers,
            timeout=300.0,
            follow_redirects=True
        )

        # Metadata for defining custom tables
        self.metadata = MetaData(schema=schema_name)

        # Logs collected during execution
        self.logs: List[str] = []

        # Progress tracking
        self._items_scraped = 0
        self._start_time = datetime.now()

    def log(self, message: str, level: str = "info"):
        """
        Log a message during scraper execution

        Args:
            message: Log message
            level: Log level (info, warning, error)
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        self.logs.append(log_entry)

        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    @abstractmethod
    async def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main scraping method - must be implemented by subclasses

        Args:
            params: Parameters for scraping (e.g., URLs, query params)

        Returns:
            List of dictionaries containing scraped data

        Raises:
            Exception: If scraping fails
        """
        pass

    async def parse_html(self, html: str, parser: str = "html.parser") -> BeautifulSoup:
        """
        Parse HTML content

        Args:
            html: HTML string
            parser: Parser to use (html.parser, lxml, html5lib)

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, parser)

    def define_tables(self) -> List[Table]:
        """
        Define custom database tables for this scraper

        Override this method to create custom tables in the scraper's schema

        Returns:
            List of SQLAlchemy Table objects

        Example:
            def define_tables(self):
                from sqlalchemy import Table, Column, Integer, String, DateTime

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
        """
        return []

    async def before_scrape(self, params: Dict[str, Any]) -> None:
        """
        Hook called before scraping starts

        Override to add custom initialization logic

        Args:
            params: Scraping parameters
        """
        pass

    async def after_scrape(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
        """
        Hook called after scraping completes

        Override to add custom cleanup or post-processing logic

        Args:
            results: Scraped results
            params: Scraping parameters
        """
        pass

    async def on_error(self, error: Exception, params: Dict[str, Any]) -> None:
        """
        Hook called when scraping fails

        Override to add custom error handling

        Args:
            error: Exception that occurred
            params: Scraping parameters
        """
        self.log(f"Error during scraping: {str(error)}", level="error")

    def get_logs(self) -> str:
        """
        Get all logs as a single string

        Returns:
            Formatted log string
        """
        return "\n".join(self.logs)

    async def report_progress(self, items_scraped: int, message: str) -> None:
        """
        Report progress to websocket subscribers

        Args:
            items_scraped: Number of items scraped so far
            message: Progress message

        Example:
            await self.report_progress(150, "Processing grid point (45.5, 3.0)...")
        """
        if self.execution_id is None:
            return

        self._items_scraped = items_scraped
        elapsed_seconds = (datetime.now() - self._start_time).total_seconds()

        # Import here to avoid circular dependency
        from app.services.progress_tracker import progress_tracker

        await progress_tracker.update_progress(
            execution_id=self.execution_id,
            status="running",
            items_scraped=items_scraped,
            elapsed_seconds=elapsed_seconds,
            message=message
        )

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds since scraper started"""
        return (datetime.now() - self._start_time).total_seconds()

    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.scraper_id}, type={self.scraper_type})>"

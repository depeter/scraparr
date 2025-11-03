"""Service for loading and running scrapers"""
import importlib
import sys
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.scrapers.base import BaseScraper
from app.models import Scraper, Execution
import logging

logger = logging.getLogger(__name__)


class ScraperRunner:
    """Load and execute scrapers"""

    @staticmethod
    def load_scraper_class(module_path: str, class_name: str) -> Type[BaseScraper]:
        """
        Dynamically load a scraper class

        Args:
            module_path: Python module path (e.g., 'scrapers.my_scraper')
            class_name: Class name (e.g., 'MyScraperClass')

        Returns:
            Scraper class

        Raises:
            ImportError: If module cannot be imported
            AttributeError: If class is not found in module
        """
        try:
            # Add scrapers directory to path if not already there
            if '/app/scrapers' not in sys.path:
                sys.path.insert(0, '/app/scrapers')

            module = importlib.import_module(module_path)
            scraper_class = getattr(module, class_name)

            if not issubclass(scraper_class, BaseScraper):
                raise TypeError(f"{class_name} must inherit from BaseScraper")

            return scraper_class

        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")
            raise
        except AttributeError as e:
            logger.error(f"Class {class_name} not found in {module_path}: {e}")
            raise

    @staticmethod
    async def run_scraper(
        db: AsyncSession,
        scraper_id: int,
        job_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Run a scraper and save execution results

        Args:
            db: Database session
            scraper_id: Scraper ID to run
            job_id: Optional job ID if this is a scheduled job
            params: Parameters to pass to scraper

        Returns:
            Execution ID

        Raises:
            ValueError: If scraper not found or inactive
        """
        params = params or {}

        # Fetch scraper from database
        result = await db.execute(select(Scraper).where(Scraper.id == scraper_id))
        scraper_config = result.scalar_one_or_none()

        if not scraper_config:
            raise ValueError(f"Scraper {scraper_id} not found")

        if not scraper_config.is_active:
            raise ValueError(f"Scraper {scraper_id} is not active")

        # Create execution record
        execution = Execution(
            scraper_id=scraper_id,
            job_id=job_id,
            status="running",
            params=params,
        )
        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        logger.info(f"Starting execution {execution.id} for scraper {scraper_id}")

        scraper_instance = None

        try:
            # Load scraper class
            scraper_class = ScraperRunner.load_scraper_class(
                scraper_config.module_path,
                scraper_config.class_name
            )

            # Instantiate scraper
            scraper_instance = scraper_class(
                scraper_id=scraper_id,
                schema_name=scraper_config.schema_name,
                config=scraper_config.config or {},
                headers=scraper_config.headers or {},
            )

            # Run before_scrape hook
            await scraper_instance.before_scrape(params)

            # Execute scraper
            results = await scraper_instance.scrape(params)

            # Run after_scrape hook
            await scraper_instance.after_scrape(results, params)

            # Update execution as successful
            execution.status = "success"
            execution.items_scraped = len(results) if results else 0
            execution.completed_at = datetime.utcnow()
            execution.logs = scraper_instance.get_logs()

            logger.info(f"Execution {execution.id} completed successfully: {execution.items_scraped} items")

        except Exception as e:
            logger.error(f"Execution {execution.id} failed: {str(e)}", exc_info=True)

            # Call error hook if scraper was instantiated
            if scraper_instance:
                try:
                    await scraper_instance.on_error(e, params)
                except Exception as hook_error:
                    logger.error(f"Error in on_error hook: {hook_error}")

            # Update execution as failed
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()

            if scraper_instance:
                execution.logs = scraper_instance.get_logs()

        finally:
            # Cleanup scraper resources
            if scraper_instance:
                try:
                    await scraper_instance.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error during scraper cleanup: {cleanup_error}")

            # Save execution
            await db.commit()
            await db.refresh(execution)

        return execution.id

    @staticmethod
    async def validate_scraper(module_path: str, class_name: str) -> Dict[str, Any]:
        """
        Validate that a scraper can be loaded

        Args:
            module_path: Python module path
            class_name: Class name

        Returns:
            Validation result with 'valid' boolean and optional 'error' message
        """
        try:
            scraper_class = ScraperRunner.load_scraper_class(module_path, class_name)

            return {
                "valid": True,
                "scraper_type": scraper_class.scraper_type.value,
                "class": class_name,
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }

"""
Tripflow ETL Scraper

This is a wrapper that allows the Tripflow ETL pipeline to be scheduled
and run through Scraparr's job scheduling system.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add ETL directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'etl'))

from app.scrapers.base import BaseScraper, ScraperType
import logging

logger = logging.getLogger(__name__)


class TripflowETLScraper(BaseScraper):
    """
    Wrapper scraper to run Tripflow ETL through Scraparr's scheduling system
    """

    @property
    def scraper_type(self) -> ScraperType:
        return ScraperType.API  # Treat as API scraper since we're calling databases

    async def scrape(self, params: dict):
        """
        Execute the Tripflow ETL pipeline

        Parameters:
            sync_type: 'full' or 'incremental' (default: 'full')
            sources: List of sources to sync (default: all)
            enable_deduplication: Whether to run deduplication (default: true)
        """
        self.log("Starting Tripflow ETL sync...")

        sync_type = params.get('sync_type', 'full')
        sources = params.get('sources', ['park4night', 'uitinvlaanderen'])
        enable_dedup = params.get('enable_deduplication', True)

        try:
            # Import the ETL module
            from tripflow_etl import TripflowETL

            # Configure ETL based on parameters
            etl = TripflowETL()

            # Override configuration if needed
            if not enable_dedup:
                import tripflow_etl
                tripflow_etl.ENABLE_DEDUPLICATION = False

            self.log(f"Sync type: {sync_type}")
            self.log(f"Sources to sync: {', '.join(sources)}")

            # Connect to databases
            await etl.connect()
            self.log("Database connections established")

            # Track results
            total_processed = 0
            total_failed = 0

            # Sync each configured source
            if 'park4night' in sources:
                self.log("Syncing Park4Night data...")
                stats = await etl.sync_park4night()
                await etl.log_sync_results(stats)

                total_processed += stats.records_processed
                total_failed += stats.records_failed

                self.log(f"Park4Night: {stats.records_processed} processed, "
                        f"{stats.records_failed} failed")

                if stats.errors:
                    for error in stats.errors[:5]:  # Log first 5 errors
                        self.log(f"Error: {error}", level="warning")

            if 'uitinvlaanderen' in sources:
                self.log("Syncing UiT in Vlaanderen data...")
                stats = await etl.sync_uitinvlaanderen()
                await etl.log_sync_results(stats)

                total_processed += stats.records_processed
                total_failed += stats.records_failed

                self.log(f"UiT: {stats.records_processed} processed, "
                        f"{stats.records_failed} failed")

                if stats.errors:
                    for error in stats.errors[:5]:  # Log first 5 errors
                        self.log(f"Error: {error}", level="warning")

            # Run post-processing
            if enable_dedup:
                self.log("Running deduplication...")
                await etl.deduplicate_locations()

            self.log("Calculating data quality metrics...")
            await etl.calculate_data_quality_metrics()

            # Disconnect
            await etl.disconnect()

            self.log(f"ETL sync completed: {total_processed} total records processed, "
                    f"{total_failed} failed")

            # Return summary
            return [{
                'sync_type': sync_type,
                'sources': sources,
                'total_processed': total_processed,
                'total_failed': total_failed,
                'success': total_failed == 0
            }]

        except Exception as e:
            self.log(f"ETL sync failed: {str(e)}", level="error")
            raise

    def define_tables(self):
        """
        No tables needed - ETL writes to Tripflow database
        """
        return []

    async def after_scrape(self, results, params):
        """
        No post-processing needed - ETL handles everything
        """
        pass
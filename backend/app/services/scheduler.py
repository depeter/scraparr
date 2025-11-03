"""Job scheduler service using APScheduler"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models import Job
from app.services.scraper_runner import ScraperRunner
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manage scheduled scraping jobs"""

    _instance: Optional['SchedulerService'] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize scheduler"""
        if self._scheduler is None:
            jobstores = {
                'default': MemoryJobStore()
            }
            self._scheduler = AsyncIOScheduler(jobstores=jobstores, timezone='UTC')
            logger.info("Scheduler initialized")

    def start(self):
        """Start the scheduler"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler shutdown")

    async def add_job(
        self,
        db: AsyncSession,
        job_id: int,
        scraper_id: int,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a job to the scheduler

        Args:
            db: Database session
            job_id: Job ID
            scraper_id: Scraper ID
            schedule_type: Type of schedule (cron, interval, once)
            schedule_config: Schedule configuration
            params: Parameters to pass to scraper

        Returns:
            Scheduler job ID

        Raises:
            ValueError: If schedule type or config is invalid
        """
        scheduler_job_id = f"job_{job_id}"

        # Remove existing job if it exists
        self.remove_job(scheduler_job_id)

        # Create trigger based on schedule type
        trigger = self._create_trigger(schedule_type, schedule_config)

        # Add job to scheduler
        self._scheduler.add_job(
            func=self._execute_scraper,
            trigger=trigger,
            id=scheduler_job_id,
            kwargs={
                "job_id": job_id,
                "scraper_id": scraper_id,
                "params": params or {},
            },
            replace_existing=True,
        )

        # Update next run time in database
        apscheduler_job = self._scheduler.get_job(scheduler_job_id)
        if apscheduler_job:
            next_run = apscheduler_job.next_run_time

            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.next_run_at = next_run
                job.scheduler_job_id = scheduler_job_id
                await db.commit()

        logger.info(f"Added job {scheduler_job_id} to scheduler")
        return scheduler_job_id

    def remove_job(self, scheduler_job_id: str):
        """
        Remove a job from the scheduler

        Args:
            scheduler_job_id: Scheduler job ID
        """
        try:
            self._scheduler.remove_job(scheduler_job_id)
            logger.info(f"Removed job {scheduler_job_id} from scheduler")
        except Exception:
            # Job doesn't exist, that's fine
            pass

    async def reload_jobs(self):
        """
        Reload all active jobs from database

        Called on startup to restore scheduled jobs
        """
        logger.info("Reloading jobs from database")

        async with async_session_maker() as db:
            result = await db.execute(
                select(Job).where(Job.is_active == True)
            )
            jobs = result.scalars().all()

            for job in jobs:
                try:
                    await self.add_job(
                        db=db,
                        job_id=job.id,
                        scraper_id=job.scraper_id,
                        schedule_type=job.schedule_type,
                        schedule_config=job.schedule_config,
                        params=job.params,
                    )
                    logger.info(f"Reloaded job {job.id}: {job.name}")
                except Exception as e:
                    logger.error(f"Failed to reload job {job.id}: {e}")

        logger.info(f"Reloaded {len(jobs)} jobs")

    def _create_trigger(self, schedule_type: str, schedule_config: Dict[str, Any]):
        """
        Create APScheduler trigger from schedule config

        Args:
            schedule_type: Type of schedule (cron, interval, once)
            schedule_config: Schedule configuration

        Returns:
            APScheduler trigger

        Raises:
            ValueError: If schedule type or config is invalid
        """
        if schedule_type == "cron":
            # Cron expression: {"expression": "0 * * * *"}
            expression = schedule_config.get("expression")
            if not expression:
                raise ValueError("Cron schedule requires 'expression' in config")

            parts = expression.split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 parts (minute hour day month day_of_week)")

            minute, hour, day, month, day_of_week = parts

            return CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone='UTC'
            )

        elif schedule_type == "interval":
            # Interval: {"seconds": 3600} or {"minutes": 60} or {"hours": 1}
            if "seconds" in schedule_config:
                return IntervalTrigger(seconds=schedule_config["seconds"])
            elif "minutes" in schedule_config:
                return IntervalTrigger(minutes=schedule_config["minutes"])
            elif "hours" in schedule_config:
                return IntervalTrigger(hours=schedule_config["hours"])
            elif "days" in schedule_config:
                return IntervalTrigger(days=schedule_config["days"])
            else:
                raise ValueError("Interval schedule requires 'seconds', 'minutes', 'hours', or 'days' in config")

        elif schedule_type == "once":
            # One-time: {"run_at": "2024-01-01T12:00:00Z"} or {"delay_seconds": 60}
            if "run_at" in schedule_config:
                run_at = datetime.fromisoformat(schedule_config["run_at"].replace("Z", "+00:00"))
                return DateTrigger(run_date=run_at, timezone='UTC')
            elif "delay_seconds" in schedule_config:
                run_at = datetime.utcnow() + timedelta(seconds=schedule_config["delay_seconds"])
                return DateTrigger(run_date=run_at, timezone='UTC')
            else:
                raise ValueError("Once schedule requires 'run_at' or 'delay_seconds' in config")

        else:
            raise ValueError(f"Invalid schedule type: {schedule_type}")

    async def _execute_scraper(self, job_id: int, scraper_id: int, params: Dict[str, Any]):
        """
        Execute a scraper (called by scheduler)

        Args:
            job_id: Job ID
            scraper_id: Scraper ID
            params: Scraper parameters
        """
        logger.info(f"Scheduler executing job {job_id} for scraper {scraper_id}")

        async with async_session_maker() as db:
            try:
                # Update last run time
                result = await db.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.last_run_at = datetime.utcnow()

                    # Update next run time
                    apscheduler_job = self._scheduler.get_job(f"job_{job_id}")
                    if apscheduler_job:
                        job.next_run_at = apscheduler_job.next_run_time

                    await db.commit()

                # Run scraper
                execution_id = await ScraperRunner.run_scraper(
                    db=db,
                    scraper_id=scraper_id,
                    job_id=job_id,
                    params=params,
                )

                logger.info(f"Job {job_id} completed with execution {execution_id}")

            except Exception as e:
                logger.error(f"Failed to execute job {job_id}: {e}", exc_info=True)


# Global scheduler instance
scheduler_service = SchedulerService()

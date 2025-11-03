"""Job model for scheduled scraping tasks"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Job(Base):
    """Scheduled job model"""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    scraper_id = Column(Integer, ForeignKey("scrapers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scheduling
    schedule_type = Column(String(50), nullable=False)  # 'cron', 'interval', 'once'
    schedule_config = Column(JSON, nullable=False)  # Cron expression or interval config
    # Example cron: {"expression": "0 * * * *"}
    # Example interval: {"seconds": 3600}

    # Parameters passed to scraper
    params = Column(JSON, nullable=True, default={})

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)

    # APScheduler job ID
    scheduler_job_id = Column(String(255), nullable=True, unique=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    scraper = relationship("Scraper", back_populates="jobs")
    executions = relationship("Execution", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(id={self.id}, name='{self.name}', scraper_id={self.scraper_id})>"

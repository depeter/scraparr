"""Execution model for tracking scraper runs"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Execution(Base):
    """Scraper execution tracking model"""

    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    scraper_id = Column(Integer, ForeignKey("scrapers.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True)

    # Execution details
    status = Column(String(50), nullable=False, default="running")  # running, success, failed, cancelled
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    items_scraped = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)  # Execution logs

    # Metadata
    params = Column(JSON, nullable=True, default={})  # Parameters used for this execution
    metrics = Column(JSON, nullable=True, default={})  # Custom metrics (e.g., response time, pages scraped)

    # Relationships
    scraper = relationship("Scraper", back_populates="executions")
    job = relationship("Job", back_populates="executions")

    def __repr__(self):
        return f"<Execution(id={self.id}, scraper_id={self.scraper_id}, status='{self.status}')>"

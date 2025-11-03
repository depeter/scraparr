"""Scraper model"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Scraper(Base):
    """Scraper configuration model"""

    __tablename__ = "scrapers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    scraper_type = Column(String(50), nullable=False)  # 'api' or 'web'

    # Python module and class information
    module_path = Column(String(500), nullable=False)  # e.g., 'scrapers.my_scraper'
    class_name = Column(String(255), nullable=False)  # e.g., 'MyScraperClass'

    # Configuration
    config = Column(JSON, nullable=True, default={})  # Custom scraper config
    headers = Column(JSON, nullable=True, default={})  # HTTP headers

    # Database schema
    schema_name = Column(String(255), nullable=True, unique=True)  # PostgreSQL schema name

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    jobs = relationship("Job", back_populates="scraper", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="scraper", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scraper(id={self.id}, name='{self.name}', type='{self.scraper_type}')>"

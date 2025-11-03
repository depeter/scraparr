"""Scraper schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ScraperBase(BaseModel):
    """Base scraper schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scraper_type: str = Field(..., pattern="^(api|web)$")
    module_path: str = Field(..., min_length=1, max_length=500)
    class_name: str = Field(..., min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = {}
    headers: Optional[Dict[str, str]] = {}
    is_active: bool = True


class ScraperCreate(ScraperBase):
    """Schema for creating a scraper"""
    pass


class ScraperUpdate(BaseModel):
    """Schema for updating a scraper"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    scraper_type: Optional[str] = Field(None, pattern="^(api|web)$")
    module_path: Optional[str] = Field(None, min_length=1, max_length=500)
    class_name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class ScraperResponse(ScraperBase):
    """Schema for scraper response"""
    id: int
    schema_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScraperListResponse(BaseModel):
    """Schema for list of scrapers"""
    total: int
    items: list[ScraperResponse]

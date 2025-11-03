"""Job schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class JobBase(BaseModel):
    """Base job schema"""
    scraper_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schedule_type: str = Field(..., pattern="^(cron|interval|once)$")
    schedule_config: Dict[str, Any] = Field(..., description="Cron expression or interval config")
    params: Optional[Dict[str, Any]] = {}
    is_active: bool = True


class JobCreate(JobBase):
    """Schema for creating a job"""
    pass


class JobUpdate(BaseModel):
    """Schema for updating a job"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schedule_type: Optional[str] = Field(None, pattern="^(cron|interval|once)$")
    schedule_config: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class JobResponse(JobBase):
    """Schema for job response"""
    id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    scheduler_job_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for list of jobs"""
    total: int
    items: list[JobResponse]

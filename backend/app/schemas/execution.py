"""Execution schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ExecutionBase(BaseModel):
    """Base execution schema"""
    scraper_id: int
    job_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = {}


class ExecutionCreate(ExecutionBase):
    """Schema for creating an execution"""
    pass


class ExecutionUpdate(BaseModel):
    """Schema for updating an execution"""
    status: Optional[str] = Field(None, pattern="^(running|success|failed|cancelled)$")
    completed_at: Optional[datetime] = None
    items_scraped: Optional[int] = None
    error_message: Optional[str] = None
    logs: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class ExecutionResponse(ExecutionBase):
    """Schema for execution response"""
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_scraped: int
    error_message: Optional[str] = None
    logs: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = {}

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """Schema for list of executions"""
    total: int
    items: list[ExecutionResponse]


class ExecutionStats(BaseModel):
    """Schema for execution statistics"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    running_executions: int
    total_items_scraped: int
    average_items_per_execution: float

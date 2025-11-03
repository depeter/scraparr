"""Pydantic schemas"""
from app.schemas.scraper import (
    ScraperCreate,
    ScraperUpdate,
    ScraperResponse,
    ScraperListResponse
)
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse
)
from app.schemas.execution import (
    ExecutionCreate,
    ExecutionUpdate,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionStats
)

__all__ = [
    "ScraperCreate",
    "ScraperUpdate",
    "ScraperResponse",
    "ScraperListResponse",
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "JobListResponse",
    "ExecutionCreate",
    "ExecutionUpdate",
    "ExecutionResponse",
    "ExecutionListResponse",
    "ExecutionStats",
]

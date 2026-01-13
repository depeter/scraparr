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
from app.schemas.auth import (
    UserBase,
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    TokenData
)
from app.schemas.system import (
    SystemStats,
    DiskUsage
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
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    "SystemStats",
    "DiskUsage",
]

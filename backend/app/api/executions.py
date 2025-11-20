"""Execution API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Execution, User
from app.schemas import (
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionStats
)

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    skip: int = 0,
    limit: int = 100,
    scraper_id: Optional[int] = None,
    job_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all executions"""
    # Build query
    query = select(Execution)

    filters = []
    if scraper_id is not None:
        filters.append(Execution.scraper_id == scraper_id)

    if job_id is not None:
        filters.append(Execution.job_id == job_id)

    if status_filter is not None:
        filters.append(Execution.status == status_filter)

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get executions
    query = query.order_by(Execution.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()

    return ExecutionListResponse(
        total=total,
        items=executions
    )


@router.get("/stats", response_model=ExecutionStats)
async def get_execution_stats(
    scraper_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get execution statistics"""
    query = select(Execution)

    if scraper_id is not None:
        query = query.where(Execution.scraper_id == scraper_id)

    result = await db.execute(query)
    executions = result.scalars().all()

    total_executions = len(executions)
    successful_executions = sum(1 for e in executions if e.status == "success")
    failed_executions = sum(1 for e in executions if e.status == "failed")
    running_executions = sum(1 for e in executions if e.status == "running")
    total_items_scraped = sum(e.items_scraped for e in executions)

    average_items = total_items_scraped / total_executions if total_executions > 0 else 0

    return ExecutionStats(
        total_executions=total_executions,
        successful_executions=successful_executions,
        failed_executions=failed_executions,
        running_executions=running_executions,
        total_items_scraped=total_items_scraped,
        average_items_per_execution=round(average_items, 2)
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get execution by ID"""
    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )

    return execution


@router.get("/{execution_id}/logs", response_model=dict)
async def get_execution_logs(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get execution logs"""
    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )

    return {
        "execution_id": execution_id,
        "logs": execution.logs or "No logs available"
    }


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete execution"""
    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )

    await db.delete(execution)
    await db.commit()

    return None

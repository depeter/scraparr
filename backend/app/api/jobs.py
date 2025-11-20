"""Job API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Job, Scraper, User
from app.schemas import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse
)
from app.services import scheduler_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    scraper_id: int = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """List all jobs"""
    # Build query
    query = select(Job)

    if scraper_id is not None:
        query = query.where(Job.scraper_id == scraper_id)

    if is_active is not None:
        query = query.where(Job.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get jobs
    query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        total=total,
        items=jobs
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new job"""

    # Verify scraper exists
    result = await db.execute(
        select(Scraper).where(Scraper.id == job_data.scraper_id)
    )
    scraper = result.scalar_one_or_none()

    if not scraper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper {job_data.scraper_id} not found"
        )

    # Create job
    job = Job(**job_data.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Add to scheduler if active
    if job.is_active:
        try:
            await scheduler_service.add_job(
                db=db,
                job_id=job.id,
                scraper_id=job.scraper_id,
                schedule_type=job.schedule_type,
                schedule_config=job.schedule_config,
                params=job.params,
            )
        except Exception as e:
            # Rollback job creation if scheduler fails
            await db.delete(job)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schedule configuration: {str(e)}"
            )

    await db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get job by ID"""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update job"""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Update fields
    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)

    # Update scheduler
    if job.is_active and job.scheduler_job_id:
        try:
            await scheduler_service.add_job(
                db=db,
                job_id=job.id,
                scraper_id=job.scraper_id,
                schedule_type=job.schedule_type,
                schedule_config=job.schedule_config,
                params=job.params,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schedule configuration: {str(e)}"
            )
    elif not job.is_active and job.scheduler_job_id:
        # Remove from scheduler if deactivated
        scheduler_service.remove_job(job.scheduler_job_id)
        job.scheduler_job_id = None
        await db.commit()

    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete job"""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Remove from scheduler
    if job.scheduler_job_id:
        scheduler_service.remove_job(job.scheduler_job_id)

    # Delete job
    await db.delete(job)
    await db.commit()

    return None


@router.post("/{job_id}/run", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def run_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Run job immediately (outside of schedule)"""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    try:
        from app.services import ScraperRunner

        execution_id = await ScraperRunner.run_scraper(
            db=db,
            scraper_id=job.scraper_id,
            job_id=job.id,
            params=job.params
        )

        return {
            "message": "Job started",
            "execution_id": execution_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run job: {str(e)}"
        )

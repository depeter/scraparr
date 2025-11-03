"""Scraper API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db, create_db_schema, drop_db_schema
from app.models import Scraper
from app.schemas import (
    ScraperCreate,
    ScraperUpdate,
    ScraperResponse,
    ScraperListResponse
)
from app.services import ScraperRunner

router = APIRouter(prefix="/scrapers", tags=["scrapers"])


@router.get("", response_model=ScraperListResponse)
async def list_scrapers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all scrapers"""
    # Count total
    count_result = await db.execute(select(func.count(Scraper.id)))
    total = count_result.scalar()

    # Get scrapers
    result = await db.execute(
        select(Scraper)
        .order_by(Scraper.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    scrapers = result.scalars().all()

    return ScraperListResponse(
        total=total,
        items=scrapers
    )


@router.post("", response_model=ScraperResponse, status_code=status.HTTP_201_CREATED)
async def create_scraper(
    scraper_data: ScraperCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scraper"""

    # Validate scraper class can be loaded
    validation = await ScraperRunner.validate_scraper(
        scraper_data.module_path,
        scraper_data.class_name
    )

    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scraper: {validation.get('error')}"
        )

    # Check if name already exists
    result = await db.execute(
        select(Scraper).where(Scraper.name == scraper_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scraper with name '{scraper_data.name}' already exists"
        )

    # Create scraper
    scraper = Scraper(**scraper_data.model_dump())

    # Generate schema name
    db.add(scraper)
    await db.flush()  # Get the ID

    scraper.schema_name = f"scraper_{scraper.id}"

    # Create PostgreSQL schema
    try:
        await create_db_schema(scraper.schema_name)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create database schema: {str(e)}"
        )

    await db.commit()
    await db.refresh(scraper)

    return scraper


@router.get("/{scraper_id}", response_model=ScraperResponse)
async def get_scraper(
    scraper_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get scraper by ID"""
    result = await db.execute(
        select(Scraper).where(Scraper.id == scraper_id)
    )
    scraper = result.scalar_one_or_none()

    if not scraper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper {scraper_id} not found"
        )

    return scraper


@router.put("/{scraper_id}", response_model=ScraperResponse)
async def update_scraper(
    scraper_id: int,
    scraper_data: ScraperUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update scraper"""
    result = await db.execute(
        select(Scraper).where(Scraper.id == scraper_id)
    )
    scraper = result.scalar_one_or_none()

    if not scraper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper {scraper_id} not found"
        )

    # Validate scraper class if module_path or class_name changed
    module_path = scraper_data.module_path or scraper.module_path
    class_name = scraper_data.class_name or scraper.class_name

    if scraper_data.module_path or scraper_data.class_name:
        validation = await ScraperRunner.validate_scraper(module_path, class_name)

        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scraper: {validation.get('error')}"
            )

    # Update fields
    update_data = scraper_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scraper, field, value)

    await db.commit()
    await db.refresh(scraper)

    return scraper


@router.delete("/{scraper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scraper(
    scraper_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete scraper"""
    result = await db.execute(
        select(Scraper).where(Scraper.id == scraper_id)
    )
    scraper = result.scalar_one_or_none()

    if not scraper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper {scraper_id} not found"
        )

    schema_name = scraper.schema_name

    # Delete scraper (cascade will delete jobs and executions)
    await db.delete(scraper)
    await db.commit()

    # Drop PostgreSQL schema
    if schema_name:
        try:
            await drop_db_schema(schema_name)
        except Exception as e:
            # Log but don't fail the request
            print(f"Warning: Failed to drop schema {schema_name}: {e}")

    return None


@router.post("/{scraper_id}/run", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def run_scraper(
    scraper_id: int,
    params: dict = {},
    db: AsyncSession = Depends(get_db)
):
    """Run scraper immediately"""
    result = await db.execute(
        select(Scraper).where(Scraper.id == scraper_id)
    )
    scraper = result.scalar_one_or_none()

    if not scraper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper {scraper_id} not found"
        )

    if not scraper.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scraper {scraper_id} is not active"
        )

    try:
        execution_id = await ScraperRunner.run_scraper(
            db=db,
            scraper_id=scraper_id,
            params=params
        )

        return {
            "message": "Scraper started",
            "execution_id": execution_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run scraper: {str(e)}"
        )


@router.post("/validate", response_model=dict)
async def validate_scraper(
    module_path: str,
    class_name: str
):
    """Validate that a scraper can be loaded"""
    validation = await ScraperRunner.validate_scraper(module_path, class_name)

    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.get("error")
        )

    return validation

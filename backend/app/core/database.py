"""Database connection and session management"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    poolclass=NullPool,
    future=True
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_db_schema(schema_name: str) -> None:
    """
    Create a new PostgreSQL schema

    Args:
        schema_name: Name of the schema to create
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        await conn.commit()


async def drop_db_schema(schema_name: str) -> None:
    """
    Drop a PostgreSQL schema

    Args:
        schema_name: Name of the schema to drop
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await conn.commit()


async def init_db() -> None:
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

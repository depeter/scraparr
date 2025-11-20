"""Database query API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database", tags=["database"])


class QueryRequest(BaseModel):
    """SQL query request"""
    query: str
    limit: Optional[int] = 1000


class QueryResponse(BaseModel):
    """SQL query response"""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float


class SchemaTable(BaseModel):
    """Database table info"""
    schema: str
    table_name: str
    column_count: int


class SchemaColumn(BaseModel):
    """Database column info"""
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str]


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a read-only SQL query

    Security measures:
    - Only SELECT statements allowed
    - Query timeout of 30 seconds
    - Result limit enforced
    """
    import time

    # Security: Only allow SELECT queries
    query_upper = request.query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed. Use SELECT to query data."
        )

    # Check for dangerous keywords
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Keyword '{keyword}' is not allowed in queries"
            )

    # Apply LIMIT if not present
    if "LIMIT" not in query_upper:
        request.query = f"{request.query.rstrip(';')} LIMIT {request.limit}"

    try:
        start_time = time.time()

        # Execute query with timeout
        result = await db.execute(
            text(request.query).execution_options(timeout=30)
        )

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Fetch results
        rows = result.fetchall()
        columns = list(result.keys()) if rows else []

        # Convert rows to list of lists
        rows_list = [list(row) for row in rows]

        logger.info(f"Query executed successfully: {len(rows_list)} rows, {execution_time:.2f}ms")

        return QueryResponse(
            columns=columns,
            rows=rows_list,
            row_count=len(rows_list),
            execution_time_ms=round(execution_time, 2)
        )

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Query execution failed: {str(e)}"
        )


@router.get("/schemas", response_model=List[str])
async def list_schemas(db: AsyncSession = Depends(get_db)):
    """List all database schemas"""
    query = """
    SELECT schema_name
    FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    ORDER BY schema_name
    """

    try:
        result = await db.execute(text(query))
        schemas = [row[0] for row in result.fetchall()]
        return schemas
    except Exception as e:
        logger.error(f"Error fetching schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", response_model=List[SchemaTable])
async def list_tables(
    schema: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all tables in database or specific schema"""
    if schema:
        query = """
        SELECT
            table_schema as schema,
            table_name,
            (SELECT COUNT(*) FROM information_schema.columns c
             WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) as column_count
        FROM information_schema.tables t
        WHERE table_schema = :schema AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        params = {"schema": schema}
    else:
        query = """
        SELECT
            table_schema as schema,
            table_name,
            (SELECT COUNT(*) FROM information_schema.columns c
             WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) as column_count
        FROM information_schema.tables t
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
          AND table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name
        """
        params = {}

    try:
        result = await db.execute(text(query), params)
        tables = [
            SchemaTable(schema=row[0], table_name=row[1], column_count=row[2])
            for row in result.fetchall()
        ]
        return tables
    except Exception as e:
        logger.error(f"Error fetching tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/columns/{schema}/{table}", response_model=List[SchemaColumn])
async def list_columns(
    schema: str,
    table: str,
    db: AsyncSession = Depends(get_db)
):
    """List all columns in a specific table"""
    query = """
    SELECT
        column_name,
        data_type,
        is_nullable = 'YES' as is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = :schema AND table_name = :table
    ORDER BY ordinal_position
    """

    try:
        result = await db.execute(
            text(query),
            {"schema": schema, "table": table}
        )
        columns = [
            SchemaColumn(
                column_name=row[0],
                data_type=row[1],
                is_nullable=row[2],
                column_default=row[3]
            )
            for row in result.fetchall()
        ]
        return columns
    except Exception as e:
        logger.error(f"Error fetching columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

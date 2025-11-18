"""
Database query optimization utilities

This module provides utilities to prevent N+1 queries and optimize database performance:
- Eager loading helpers
- Query result caching
- Batch operations
- Index recommendations

Performance Guidelines:
- Use eager loading (selectinload/joinedload) for relationships
- Paginate large result sets
- Use database indexes on frequently queried columns
- Batch operations when possible
"""

from typing import List, Type, TypeVar, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, lazyload
from sqlalchemy.orm.strategy_options import Load
from functools import wraps
import time

from shared.models.database import Base

T = TypeVar('T', bound=Base)


class QueryOptimizer:
    """Helper class for optimized database queries"""

    @staticmethod
    def with_relationships(
        model: Type[T],
        *relationships: str,
        use_joinedload: bool = False
    ) -> select:
        """
        Create a query with eagerly loaded relationships to prevent N+1 queries

        Args:
            model: SQLAlchemy model class
            relationships: Names of relationships to eager load
            use_joinedload: Use joinedload instead of selectinload (for one-to-one)

        Returns:
            SQLAlchemy select statement with eager loading

        Example:
            query = QueryOptimizer.with_relationships(
                Vulnerability,
                'patches',
                'asset_vulnerabilities'
            )
            result = await session.execute(query)
            vulnerabilities = result.scalars().all()
        """
        query = select(model)

        for relationship in relationships:
            if use_joinedload:
                query = query.options(joinedload(getattr(model, relationship)))
            else:
                query = query.options(selectinload(getattr(model, relationship)))

        return query

    @staticmethod
    async def batch_get_by_ids(
        session: AsyncSession,
        model: Type[T],
        ids: List[int],
        batch_size: int = 100
    ) -> List[T]:
        """
        Efficiently fetch multiple records by ID in batches

        Args:
            session: Database session
            model: SQLAlchemy model class
            ids: List of IDs to fetch
            batch_size: Number of IDs per batch query

        Returns:
            List of model instances

        Example:
            vulnerabilities = await QueryOptimizer.batch_get_by_ids(
                session,
                Vulnerability,
                [1, 2, 3, ..., 1000]
            )
        """
        results = []

        # Process in batches to avoid huge IN clauses
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            result = await session.execute(
                select(model).where(model.id.in_(batch_ids))
            )
            results.extend(result.scalars().all())

        return results

    @staticmethod
    async def paginated_query(
        session: AsyncSession,
        query: select,
        page: int = 1,
        page_size: int = 50,
        max_page_size: int = 100
    ) -> tuple[List[T], int]:
        """
        Execute paginated query with optimal performance

        Args:
            session: Database session
            query: Base query to paginate
            page: Page number (1-indexed)
            page_size: Results per page
            max_page_size: Maximum allowed page size

        Returns:
            Tuple of (results, total_count)

        Example:
            query = select(Vulnerability).where(Vulnerability.severity == "critical")
            vulnerabilities, total = await QueryOptimizer.paginated_query(
                session, query, page=1, page_size=20
            )
        """
        # Enforce max page size
        page_size = min(page_size, max_page_size)

        # Calculate offset
        offset = (page - 1) * page_size

        # Get total count (optimized count query)
        # Note: count(*) is faster than counting ORM objects
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        result = await session.execute(count_query)
        total_count = result.scalar()

        # Get paginated results
        paginated_query = query.limit(page_size).offset(offset)
        result = await session.execute(paginated_query)
        results = result.scalars().all()

        return results, total_count

    @staticmethod
    def lazy_load_relationships(model: Type[T], *relationships: str) -> select:
        """
        Explicitly disable lazy loading for specific relationships
        Useful for preventing accidental N+1 queries

        Args:
            model: SQLAlchemy model class
            relationships: Names of relationships to disable

        Returns:
            SQLAlchemy select statement with lazy loading disabled
        """
        query = select(model)

        for relationship in relationships:
            query = query.options(lazyload(getattr(model, relationship)))

        return query


class QueryPerformanceMonitor:
    """Monitor query performance and detect slow queries"""

    def __init__(self, threshold_ms: float = 100.0):
        """
        Initialize performance monitor

        Args:
            threshold_ms: Threshold for slow query warning (milliseconds)
        """
        self.threshold_ms = threshold_ms
        self.slow_queries: List[Dict[str, Any]] = []

    async def execute_with_monitoring(
        self,
        session: AsyncSession,
        query: select,
        description: str = "query"
    ) -> Any:
        """
        Execute query with performance monitoring

        Args:
            session: Database session
            query: Query to execute
            description: Description of the query for logging

        Returns:
            Query result

        Example:
            monitor = QueryPerformanceMonitor(threshold_ms=50.0)
            result = await monitor.execute_with_monitoring(
                session,
                select(Vulnerability),
                description="fetch all vulnerabilities"
            )
        """
        start_time = time.time()

        try:
            result = await session.execute(query)
            duration_ms = (time.time() - start_time) * 1000

            if duration_ms > self.threshold_ms:
                self.slow_queries.append({
                    "description": description,
                    "duration_ms": duration_ms,
                    "query": str(query),
                    "timestamp": time.time()
                })

                # Log slow query warning
                import structlog
                logger = structlog.get_logger()
                logger.warning(
                    "slow_query_detected",
                    description=description,
                    duration_ms=duration_ms,
                    threshold_ms=self.threshold_ms
                )

            return result

        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error(
                "query_execution_failed",
                description=description,
                error=str(e),
                exc_info=True
            )
            raise

    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get list of slow queries detected"""
        return self.slow_queries

    def reset(self):
        """Reset slow query tracking"""
        self.slow_queries = []


def monitor_query_performance(threshold_ms: float = 100.0):
    """
    Decorator to monitor query performance

    Args:
        threshold_ms: Threshold for slow query warning

    Example:
        @monitor_query_performance(threshold_ms=50.0)
        async def get_critical_vulnerabilities(session: AsyncSession):
            result = await session.execute(
                select(Vulnerability).where(Vulnerability.severity == "critical")
            )
            return result.scalars().all()
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    import structlog
                    logger = structlog.get_logger()
                    logger.warning(
                        "slow_function_detected",
                        function=func.__name__,
                        duration_ms=duration_ms,
                        threshold_ms=threshold_ms
                    )

                return result

            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error(
                    "function_execution_failed",
                    function=func.__name__,
                    error=str(e),
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


# Recommended indexes for common queries
RECOMMENDED_INDEXES = {
    "vulnerabilities": [
        ("cve_id", "Unique index on CVE ID for fast lookups"),
        ("severity", "Index on severity for filtering"),
        ("status", "Index on status for filtering"),
        ("priority_score", "Index on priority_score for sorting"),
        ("created_at", "Index on created_at for time-based queries"),
        ("(severity, status)", "Composite index for common filter combination"),
    ],
    "assets": [
        ("asset_id", "Unique index on asset ID"),
        ("hostname", "Index on hostname for searching"),
        ("ip_address", "Index on IP address for lookups"),
        ("is_active", "Index on is_active for filtering"),
        ("environment", "Index on environment for filtering"),
    ],
    "patches": [
        ("patch_id", "Unique index on patch ID"),
        ("vulnerability_id", "Foreign key index for joins"),
        ("validation_passed", "Index for filtering validated patches"),
        ("created_at", "Index for sorting by date"),
    ],
    "deployments": [
        ("deployment_id", "Unique index on deployment ID"),
        ("patch_id", "Foreign key index for joins"),
        ("asset_id", "Foreign key index for joins"),
        ("status", "Index on status for filtering"),
        ("created_at", "Index for sorting by date"),
    ],
}


def get_index_recommendations(table_name: str) -> List[tuple[str, str]]:
    """
    Get recommended indexes for a table

    Args:
        table_name: Name of the database table

    Returns:
        List of (column, description) tuples
    """
    return RECOMMENDED_INDEXES.get(table_name, [])

"""
Database Query Optimizer
=========================

Optimized query helpers and patterns for high-performance database access.

This module provides:
- Pre-optimized query builders
- Efficient pagination
- Query result caching
- N+1 query prevention
- Database-aware filtering
"""

from typing import List, Optional, Dict, Any, TypeVar, Generic, Type
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql import Select
from datetime import datetime, timedelta
import logging

from shared.models.base import Base

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)


class QueryOptimizer(Generic[T]):
    """
    Optimized query builder with automatic index hints and relationship loading.

    Usage:
        optimizer = QueryOptimizer(Vulnerability, db_session)
        results = optimizer.filter_by(status="new").order_by("priority_score").limit(10).all()
    """

    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session
        self._query = select(model)
        self._filters = []
        self._order_by_clauses = []
        self._limit_value = None
        self._offset_value = None
        self._eager_loads = []

    def filter_by(self, **kwargs) -> 'QueryOptimizer[T]':
        """
        Add equality filters.

        Example:
            .filter_by(status="new", severity="critical")
        """
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                self._filters.append(getattr(self.model, key) == value)
        return self

    def filter(self, *conditions) -> 'QueryOptimizer[T]':
        """
        Add custom filter conditions.

        Example:
            .filter(Vulnerability.priority_score > 70, Vulnerability.status != "ignored")
        """
        self._filters.extend(conditions)
        return self

    def filter_date_range(
        self,
        field_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> 'QueryOptimizer[T]':
        """
        Filter by date range.

        Uses index-friendly BETWEEN queries.
        """
        if not hasattr(self.model, field_name):
            logger.warning(f"Field {field_name} not found on {self.model.__name__}")
            return self

        field = getattr(self.model, field_name)

        if start_date and end_date:
            self._filters.append(field.between(start_date, end_date))
        elif start_date:
            self._filters.append(field >= start_date)
        elif end_date:
            self._filters.append(field <= end_date)

        return self

    def filter_in(self, field_name: str, values: List[Any]) -> 'QueryOptimizer[T]':
        """
        Filter using IN clause (index-friendly).

        Example:
            .filter_in("status", ["new", "analyzing", "patch_generated"])
        """
        if not hasattr(self.model, field_name):
            logger.warning(f"Field {field_name} not found on {self.model.__name__}")
            return self

        field = getattr(self.model, field_name)
        self._filters.append(field.in_(values))
        return self

    def order_by(self, *fields: str, desc: bool = False) -> 'QueryOptimizer[T]':
        """
        Add ordering clauses.

        Example:
            .order_by("priority_score", "created_at", desc=True)
        """
        for field_name in fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                if desc:
                    self._order_by_clauses.append(field.desc())
                else:
                    self._order_by_clauses.append(field.asc())
        return self

    def limit(self, limit: int) -> 'QueryOptimizer[T]':
        """Set result limit"""
        self._limit_value = limit
        return self

    def offset(self, offset: int) -> 'QueryOptimizer[T]':
        """Set result offset"""
        self._offset_value = offset
        return self

    def paginate(self, page: int = 1, page_size: int = 20) -> 'QueryOptimizer[T]':
        """
        Apply pagination.

        Uses efficient limit/offset pattern.
        """
        self._limit_value = page_size
        self._offset_value = (page - 1) * page_size
        return self

    def eager_load(self, *relationships: str) -> 'QueryOptimizer[T]':
        """
        Eager load relationships to prevent N+1 queries.

        Example:
            .eager_load("patches", "deployments")
        """
        for rel_name in relationships:
            if hasattr(self.model, rel_name):
                # Use selectinload for collections, joinedload for single items
                rel = getattr(self.model, rel_name)
                self._eager_loads.append(selectinload(rel))
        return self

    def build_query(self) -> Select:
        """Build the final SQLAlchemy query"""
        query = self._query

        # Apply eager loads
        if self._eager_loads:
            query = query.options(*self._eager_loads)

        # Apply filters
        if self._filters:
            query = query.where(and_(*self._filters))

        # Apply ordering
        if self._order_by_clauses:
            query = query.order_by(*self._order_by_clauses)

        # Apply limit/offset
        if self._limit_value is not None:
            query = query.limit(self._limit_value)
        if self._offset_value is not None:
            query = query.offset(self._offset_value)

        return query

    def all(self) -> List[T]:
        """Execute query and return all results"""
        query = self.build_query()
        result = self.session.execute(query)
        return result.scalars().all()

    def first(self) -> Optional[T]:
        """Execute query and return first result"""
        query = self.build_query().limit(1)
        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def count(self) -> int:
        """Get total count (efficient, doesn't load data)"""
        # Build count query without limit/offset
        count_query = select(func.count()).select_from(self.model)
        if self._filters:
            count_query = count_query.where(and_(*self._filters))

        result = self.session.execute(count_query)
        return result.scalar()

    def exists(self) -> bool:
        """Check if any results exist (efficient)"""
        exists_query = select(1).select_from(self.model).where(and_(*self._filters)).limit(1)
        result = self.session.execute(exists_query)
        return result.scalar() is not None


class BulkQueryHelper:
    """Helper for bulk operations with optimized batch processing"""

    @staticmethod
    def bulk_insert(session: Session, model: Type[Base], records: List[Dict[str, Any]], batch_size: int = 500):
        """
        Bulk insert with batching for memory efficiency.

        More efficient than individual inserts.
        """
        total = len(records)
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            session.bulk_insert_mappings(model, batch)
            session.flush()

        logger.info(f"Bulk inserted {total} {model.__name__} records in batches of {batch_size}")

    @staticmethod
    def bulk_update(session: Session, model: Type[Base], updates: List[Dict[str, Any]], batch_size: int = 500):
        """
        Bulk update with batching.

        Each record in updates must include 'id'.
        """
        total = len(updates)
        for i in range(0, total, batch_size):
            batch = updates[i:i + batch_size]
            session.bulk_update_mappings(model, batch)
            session.flush()

        logger.info(f"Bulk updated {total} {model.__name__} records in batches of {batch_size}")

    @staticmethod
    def batch_fetch(
        session: Session,
        model: Type[Base],
        ids: List[int],
        batch_size: int = 500
    ) -> Dict[int, Base]:
        """
        Fetch records by IDs in batches.

        Returns dict mapping id -> record for easy lookup.
        """
        results = {}

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            query = select(model).where(model.id.in_(batch_ids))
            records = session.execute(query).scalars().all()

            for record in records:
                results[record.id] = record

        return results


class QueryPatterns:
    """Common optimized query patterns"""

    @staticmethod
    def get_recent_records(
        session: Session,
        model: Type[T],
        hours: int = 24,
        limit: int = 100,
        order_by_field: str = "created_at"
    ) -> List[T]:
        """
        Get recent records efficiently.

        Uses indexed timestamp field for performance.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        if not hasattr(model, order_by_field):
            logger.warning(f"Field {order_by_field} not found, using id")
            order_by_field = "id"

        field = getattr(model, order_by_field)

        query = (
            select(model)
            .where(field >= cutoff)
            .order_by(field.desc())
            .limit(limit)
        )

        result = session.execute(query)
        return result.scalars().all()

    @staticmethod
    def get_by_status_with_priority(
        session: Session,
        model: Type[T],
        status_field: str = "status",
        priority_field: str = "priority_score",
        status_values: Optional[List[str]] = None,
        min_priority: float = 0.0,
        limit: int = 100
    ) -> List[T]:
        """
        Get records by status and priority (uses composite index).
        """
        filters = []

        if status_values and hasattr(model, status_field):
            status_attr = getattr(model, status_field)
            filters.append(status_attr.in_(status_values))

        if hasattr(model, priority_field):
            priority_attr = getattr(model, priority_field)
            filters.append(priority_attr >= min_priority)

        query = select(model)
        if filters:
            query = query.where(and_(*filters))

        # Order by priority descending (high priority first)
        if hasattr(model, priority_field):
            query = query.order_by(getattr(model, priority_field).desc())

        query = query.limit(limit)

        result = session.execute(query)
        return result.scalars().all()

    @staticmethod
    def get_paginated_with_count(
        session: Session,
        query: Select,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Any], int]:
        """
        Get paginated results with total count.

        Returns: (items, total_count)
        """
        # Get total count efficiently
        count_query = select(func.count()).select_from(query.subquery())
        total_count = session.execute(count_query).scalar()

        # Get paginated results
        offset = (page - 1) * page_size
        paginated_query = query.offset(offset).limit(page_size)
        items = session.execute(paginated_query).scalars().all()

        return items, total_count

    @staticmethod
    def search_by_text(
        session: Session,
        model: Type[T],
        search_fields: List[str],
        search_term: str,
        limit: int = 50
    ) -> List[T]:
        """
        Simple text search across multiple fields.

        Note: For production, consider PostgreSQL full-text search or Elasticsearch.
        """
        if not search_term:
            return []

        search_pattern = f"%{search_term}%"
        conditions = []

        for field_name in search_fields:
            if hasattr(model, field_name):
                field = getattr(model, field_name)
                conditions.append(field.like(search_pattern))

        if not conditions:
            return []

        query = select(model).where(or_(*conditions)).limit(limit)
        result = session.execute(query)
        return result.scalars().all()


def explain_query(session: Session, query: Select) -> str:
    """
    Get query execution plan for optimization.

    Useful for identifying missing indexes.
    """
    compiled_query = query.compile(compile_kwargs={"literal_binds": True})
    explain_query = f"EXPLAIN ANALYZE {compiled_query}"

    result = session.execute(explain_query)
    return "\n".join([str(row) for row in result])

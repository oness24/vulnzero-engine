"""
VulnZero - Base Database Model
Common fields and functionality for all models
"""

from datetime import datetime
from typing import Any
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


class CustomBase:
    """
    Base class with common fields for all models.
    All tables will have these fields automatically.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Automatically generate table name from class name.
        Example: UserAccount -> user_account
        """
        import re
        name = cls.__name__
        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return name

    # Primary key (all tables have an ID)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Timestamps (automatically managed)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when record was created"
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when record was last updated"
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime to ISO format string
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """
        Update model instance from dictionary.

        Args:
            data: Dictionary with field names and values
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of the model"""
        class_name = self.__class__.__name__
        return f"<{class_name}(id={self.id})>"


# Create declarative base with our custom base class
Base = declarative_base(cls=CustomBase)


# Mixin classes for common functionality
class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    Records are marked as deleted instead of being removed from database.
    """

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when record was soft deleted"
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted"""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted"""
        self.deleted_at = func.now()

    def restore(self) -> None:
        """Restore soft deleted record"""
        self.deleted_at = None

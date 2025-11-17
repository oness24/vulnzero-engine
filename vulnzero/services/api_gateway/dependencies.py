"""API dependencies and utilities."""
from typing import Generator

from sqlalchemy.orm import Session

from vulnzero.services.patch_generator.storage import PatchStorageService
from vulnzero.shared.models import get_db


def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session dependency.

    Yields:
        Database session
    """
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def get_storage_service(db: Session) -> PatchStorageService:
    """
    Get patch storage service.

    Args:
        db: Database session

    Returns:
        PatchStorageService instance
    """
    return PatchStorageService(db)

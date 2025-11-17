"""
VulnZero - Database Configuration
SQLAlchemy engine and session management
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from shared.config.settings import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.database_echo,  # Log SQL queries
    future=True,  # Use SQLAlchemy 2.0 style
)


# Configure connection pool events
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance (if using SQLite)"""
    if "sqlite" in settings.database_url:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


@event.listens_for(Engine, "connect")
def set_postgres_settings(dbapi_conn, connection_record):
    """Set PostgreSQL session settings"""
    if "postgresql" in settings.database_url:
        cursor = dbapi_conn.cursor()
        cursor.execute("SET timezone='UTC'")
        cursor.close()


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database - create all tables.
    This should only be used in development or for testing.
    In production, use Alembic migrations.
    """
    from shared.models.base import Base
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    Drop all database tables.
    WARNING: This will delete all data!
    Only use in development/testing.
    """
    from shared.models.base import Base
    Base.metadata.drop_all(bind=engine)


def get_db_context() -> Session:
    """
    Get database session for use in context manager.

    Usage:
        with get_db_context() as db:
            db.query(User).all()

    Returns:
        Session: SQLAlchemy database session
    """
    return SessionLocal()

"""
VulnZero - Shared Configuration Module
"""

from shared.config.database import get_db, engine, SessionLocal
from shared.config.settings import settings

__all__ = ["get_db", "engine", "SessionLocal", "settings"]
"""Configuration module for VulnZero"""

from shared.config.settings import Settings, settings

__all__ = ["Settings", "settings"]

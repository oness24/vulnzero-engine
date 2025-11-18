"""
VulnZero Shared Module

Shared utilities, models, and configuration used across all services.
"""

__version__ = "0.1.0"
"""Shared modules for VulnZero"""

from shared.celery_app import app as celery_app

__all__ = ["celery_app"]

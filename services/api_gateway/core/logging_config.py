"""
VulnZero API Gateway - Logging Configuration
Structured logging setup with JSON formatting
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger

from shared.config.settings import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    Uses JSON format for production, human-readable for development.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # JSON Formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        }
    )

    # Console formatter (human-readable for development)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    if settings.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.log_level.upper()))

        # Use JSON in production, human-readable in development
        if settings.log_format == "json" and settings.is_production:
            console_handler.setFormatter(json_formatter)
        else:
            console_handler.setFormatter(console_formatter)

        root_logger.addHandler(console_handler)

    # File Handler
    if settings.log_to_file:
        file_handler = logging.FileHandler(settings.log_file_path)
        file_handler.setLevel(getattr(logging, settings.log_level.upper()))
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

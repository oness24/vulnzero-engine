"""
Celery Application Configuration

Celery app for vulnerability aggregation tasks.
"""

from celery import Celery
from celery.schedules import crontab
import os

# Create Celery app
celery_app = Celery(
    "vulnzero_aggregator",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "scan-wazuh-every-6-hours": {
        "task": "services.aggregator.tasks.scan_tasks.scan_wazuh",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    "scan-qualys-every-6-hours": {
        "task": "services.aggregator.tasks.scan_tasks.scan_qualys",
        "schedule": crontab(minute=15, hour="*/6"),  # Every 6 hours, offset by 15min
    },
    "scan-tenable-every-6-hours": {
        "task": "services.aggregator.tasks.scan_tasks.scan_tenable",
        "schedule": crontab(minute=30, hour="*/6"),  # Every 6 hours, offset by 30min
    },
    "enrich-vulnerabilities-daily": {
        "task": "services.aggregator.tasks.enrichment_tasks.enrich_new_vulnerabilities",
        "schedule": crontab(minute=0, hour=2),  # Daily at 2 AM UTC
    },
    "calculate-priorities-daily": {
        "task": "services.aggregator.tasks.priority_tasks.recalculate_all_priorities",
        "schedule": crontab(minute=0, hour=3),  # Daily at 3 AM UTC
    },
}

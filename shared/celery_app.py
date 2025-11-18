"""
Shared Celery application for VulnZero
"""

from celery import Celery
from shared.config import settings

# Create Celery app
app = Celery(
    "vulnzero",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=settings.celery_task_track_started,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 1 hour
)

# Auto-discover tasks from all services
app.autodiscover_tasks([
    'services.aggregator',
    'services.patch_generator',
    'services.testing_engine',
    'services.deployment_engine',
    'services.monitoring',
])


# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'scan-vulnerabilities': {
        'task': 'services.aggregator.tasks.scan_all_sources',
        'schedule': settings.scan_interval_hours * 3600,  # Convert hours to seconds
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


if __name__ == '__main__':
    app.start()

"""
Celery configuration for Cars Portal project.
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')

app = Celery('yallamotor_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'warm-cache-every-hour': {
        'task': 'parts.tasks.warm_cache_task',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-expired-carts': {
        'task': 'parts.tasks.cleanup_expired_carts',
        'schedule': 86400.0,  # Every day
    },
    'update-popular-parts': {
        'task': 'parts.tasks.update_popular_parts_cache',
        'schedule': 1800.0,  # Every 30 minutes
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
import os
from celery import Celery

# Set default Django settings module
# remove this
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PFD_agent.settings.local')

# Create Celery app
app = Celery('PFD_agent')

# Configure Celery using settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Optional: Configure task routing if you want different queues later
#app.conf.task_routes = {
#    'pfd_bench.tasks.*': {'queue': 'pfd_processing'},
#}
import os
from celery import Celery

# Default Django settings module for 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ocloud_billing.settings')

app = Celery('Ocloud_billing')

# Load settings from Django, using CELERY_ prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

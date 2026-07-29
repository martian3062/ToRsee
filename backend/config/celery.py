import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("torsy")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.imports = ("osint.schedules",)
app.conf.beat_schedule = {
    "dispatch-due-monitored-targets": {
        "task": "osint.dispatch_due_monitored_targets",
        "schedule": 60.0,
        "options": {"expires": 55},
    }
}
app.autodiscover_tasks()

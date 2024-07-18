import importlib.util
import os
import sys

if importlib.util.find_spec("common") is None:
    sys.path.append(
        os.path.abspath(os.path.join("..", "pkg"))
    )  # Import pkg without install

from celery import Celery
from common.celery.routing import (
    setup_organization_task_routing,
    setup_synchronous_model_task_routing,
)
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "device_service.settings.local")
app = Celery("device_service")
app.config_from_object("django.conf:settings", namespace="CELERY")

setup_organization_task_routing()
setup_synchronous_model_task_routing()

app.autodiscover_tasks(settings.CELERY_TASKS)

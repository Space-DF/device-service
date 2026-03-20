import importlib.util
import os
import sys

if importlib.util.find_spec("common") is None:
    sys.path.append(
        os.path.abspath(os.path.join("..", "django-common-utils"))
    )  # Import django-common-utils without install


from celery import Celery
from common.celery.routing import (
    setup_organization_task_routing,
    setup_synchronous_model_task_routing,
)
from django.conf import settings
from dotenv import load_dotenv
from kombu import Exchange, Queue

load_dotenv()


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "device_service.settings")
app = Celery("device_service")
app.config_from_object("django.conf:settings", namespace="CELERY")

setup_organization_task_routing()
setup_synchronous_model_task_routing()

# Register queue for receiving location updates from transformer-service
if app.conf.task_queues is None:
    app.conf.task_queues = ()
if app.conf.task_routes is None:
    app.conf.task_routes = {}

LOCATION_QUEUE = "update_device_location"

app.conf.task_queues += (
    Queue(
        LOCATION_QUEUE,
        exchange=Exchange(LOCATION_QUEUE, type="direct"),
        routing_key=LOCATION_QUEUE,
        queue_arguments={"x-single-active-consumer": True},
    ),
)
app.conf.task_routes[f"spacedf.tasks.{LOCATION_QUEUE}"] = {
    "queue": LOCATION_QUEUE,
    "routing_key": LOCATION_QUEUE,
}

app.autodiscover_tasks(settings.CELERY_TASKS)

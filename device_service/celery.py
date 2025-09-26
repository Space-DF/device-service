import importlib.util
import os
import sys

from kombu import Exchange, Queue

if importlib.util.find_spec("common") is None:
    sys.path.append(
        os.path.abspath(os.path.join("..", "django-common-utils"))
    )  # Import django-common-utils without install

import json
import logging

from celery import Celery, bootsteps
from common.celery.routing import (
    setup_organization_task_routing,
    setup_synchronous_model_task_routing,
)
from django.conf import settings
from dotenv import load_dotenv
from kombu import Consumer

load_dotenv()

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "device_service.settings")
app = Celery("device_service")

# Load settings first
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks
app.autodiscover_tasks(settings.CELERY_TASKS)

# Apply topic-based routing using the common functions
setup_organization_task_routing()
setup_synchronous_model_task_routing()

# Get the device queue that was created by the routing functions
device_queue = None
for queue in app.conf.task_queues:
    if queue.name == "device-service":
        device_queue = queue
        break

# Add transformer queue for device data processing
transformer_queue = Queue(
    settings.TRANSFORMER_DEVICE_QUEUE,
    exchange=Exchange(settings.TRANSFORMER_AMQP_EXCHANGE, type="topic"),
    routing_key=settings.TRANSFORMER_AMQP_ROUTING_KEY,
)

# Combine topic-based queue with transformer queue
if device_queue:
    app.conf.task_queues = (device_queue, transformer_queue)
else:
    # Fallback: create device queue if routing functions didn't work
    device_queue = Queue(
        "device-service",
        exchange=Exchange("app.events", type="topic"),
        routing_key="*.*.*",
        queue_arguments={"x-single-active-consumer": True},
    )
    app.conf.task_queues = (device_queue, transformer_queue)
app.conf.task_routes["device.ingest_transformed_data"] = {
    "queue": settings.TRANSFORMER_DEVICE_QUEUE,
    "routing_key": settings.TRANSFORMER_AMQP_ROUTING_KEY,
}
for queue in app.conf.task_queues:
    print(f"  {queue.name}: {queue.routing_key}")


class TransformerConsumerStep(bootsteps.ConsumerStep):
    """Custom consumer for raw JSON messages from transformer-service"""

    def get_consumers(self, channel):
        transformer_queue = Queue(
            settings.TRANSFORMER_DEVICE_QUEUE,
            exchange=Exchange(settings.TRANSFORMER_AMQP_EXCHANGE, type="topic"),
            routing_key=settings.TRANSFORMER_AMQP_ROUTING_KEY,
        )

        return [
            Consumer(
                channel,
                queues=[transformer_queue],
                callbacks=[self.handle_transformer_message],
                accept=["json", "text/plain", "application/json"],
                no_ack=False,
            )
        ]

    def handle_transformer_message(self, body, message):
        """Process raw JSON from transformer-service"""
        try:
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body

            logger.info(
                f"Received transformer message for device_eui: {data.get('device_eui')}"
            )

            from apps.device.tasks import process_device_data

            process_device_data(data)

            message.ack()
            logger.info(
                f"Successfully processed transformer message for device_eui: {data.get('device_eui')}"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in transformer message: {e}")
            message.reject(requeue=False)  # Don't requeue invalid JSON

        except Exception as e:
            logger.error(f"Error processing transformer message: {e}", exc_info=True)
            message.reject(requeue=True)


app.steps["consumer"].add(TransformerConsumerStep)

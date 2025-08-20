import json
import logging

from celery import shared_task
from django.db import transaction
from django_tenants.utils import get_tenant_domain_model, tenant_context

from apps.device.models import DeviceTransformedData

logger = logging.getLogger(__name__)


def process_device_data(data: dict):
    """Process transformed device data"""

    organization_schema = data["organization"]
    device_eui = data["device_eui"]
    device_reference = data.get("device_id")
    timestamp = data["timestamp"]

    # Get tenant
    domain_model = get_tenant_domain_model()
    domain = domain_model.objects.select_related("tenant").get(
        tenant__schema_name=organization_schema
    )

    logger.info(
        f"Processing device_id: {device_reference}, device_eui: {device_eui}, tenant: {organization_schema}"
    )

    with tenant_context(domain.tenant):
        with transaction.atomic():
            transformed_data = DeviceTransformedData.objects.create(
                device_eui=device_eui,
                device_reference=device_reference,
                data={
                    "location": data.get("location", {}),
                },
                timestamp=timestamp,
                source=data["source"],
                metadata=data["metadata"],
            )

            logger.info(
                f"Created DeviceTransformedData ID: {transformed_data.id} for device_id: {device_reference}"
            )
            return True


@shared_task(
    bind=True,
    name="device.ingest_transformed_data",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=300,
    autoretry_for=(Exception,),
    dont_autoretry_for=(KeyError, ValueError, json.JSONDecodeError),
)
def ingest_transformed_data(self, message):
    """Celery task to process transformed device data"""

    data = json.loads(message) if isinstance(message, str) else message

    logger.info(
        f"Processing task for device_id: {data['device_id']} ({data['device_eui']}) in tenant: {data['organization']}"
    )

    process_device_data(data)

    return f"Successfully processed device_id: {data['device_id']} in tenant: {data['organization']}"

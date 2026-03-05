import logging

from common.celery.tasks import tenant_shared_task
from django.contrib.gis.geos import Point

from apps.device.models import SpaceDevice

logger = logging.getLogger(__name__)


@tenant_shared_task(name="spacedf.tasks.update_device_location")
def update_device_location(device_id: str, latitude: float, longitude: float):
    try:
        space_device = SpaceDevice.objects.get(device_id=device_id)
    except SpaceDevice.DoesNotExist:
        logger.warning(
            f"SpaceDevice with device_id={device_id} not found, skipping location update"
        )
        return

    space_device.location = Point(longitude, latitude, srid=4326)
    space_device.save(update_fields=["location", "updated_at"])

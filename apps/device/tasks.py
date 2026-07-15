import logging

from common.celery.tasks import tenant_shared_task
from django_tenants.utils import schema_context

from apps.device.models import Device, SpaceDevice

logger = logging.getLogger(__name__)


@tenant_shared_task(name="spacedf.tasks.device_downgrade")
def device_downgrade_task(**kwargs):
    return deactivate_excess_devices(kwargs["org_slug"], kwargs.get("limits"))


@tenant_shared_task(name="spacedf.tasks.device_upgrade")
def device_upgrade_task(**kwargs):
    return reactivate_devices(kwargs["org_slug"])


@tenant_shared_task(name="spacedf.tasks.update_device_location")
def update_device_location(device_id: str, latitude: float, longitude: float):
    try:
        space_device = SpaceDevice.objects.get(device_id=device_id)
    except SpaceDevice.DoesNotExist:
        logger.warning(
            f"SpaceDevice with device_id={device_id} not found, skipping location update"
        )
        return

    space_device.location = {
        "latitude": latitude,
        "longitude": longitude,
    }
    space_device.save(update_fields=["location", "updated_at"])


def deactivate_excess_devices(organization_slug: str, limits: dict = None) -> int:
    limits = limits or {}
    max_devices = limits.get("device.max_count")
    if max_devices is None:
        logger.warning(
            "Skipping device deactivation for %s: device.max_count not in event",
            organization_slug,
        )
        return 0

    with schema_context(organization_slug):
        active_device_ids = SpaceDevice.objects.filter(
            space__slug_name=organization_slug,
            device__is_deactivated=False,
        ).values_list("device_id", flat=True)

        devices = Device.objects.filter(
            id__in=active_device_ids,
            is_deactivated=False,
        ).order_by("created_at")

        excess_ids = list(devices.values_list("id", flat=True)[max_devices:])
        count = (
            Device.objects.filter(id__in=excess_ids).update(is_deactivated=True)
            if excess_ids
            else 0
        )
        if count:
            logger.info(
                "Downgrade: deactivated %s excess devices for org %s "
                "(kept %s active out of %s total).",
                count,
                organization_slug,
                min(len(devices), max_devices),
                len(devices),
            )
        return count


def reactivate_devices(organization_slug: str) -> int:
    """
    Reactivate devices that were deactivated during a prior downgrade.
    """
    with schema_context(organization_slug):
        count = Device.objects.filter(is_deactivated=True).update(is_deactivated=False)
        if count:
            logger.info(
                "Renewal: reactivated %s devices for org %s.",
                count,
                organization_slug,
            )
        return count

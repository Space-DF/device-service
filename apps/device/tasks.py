import logging

from common.celery.tasks import task, tenant_shared_task
from django_tenants.utils import schema_context

from apps.device.models import Device, SpaceDevice

logger = logging.getLogger(__name__)


@task(
    name="spacedf.tasks.device_downgrade",
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=3,
)
def device_downgrade_task(**kwargs):
    org_slug = kwargs["org_slug"]
    limits = kwargs.get("limits") or {}
    max_devices = limits.get("device.max_count")
    if max_devices is None:
        logger.warning(
            "Skipping device deactivation for %s: device.max_count not in event",
            org_slug,
        )
        return 0

    with schema_context(org_slug):
        active_device_ids = SpaceDevice.objects.filter(
            space__slug_name=org_slug,
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
                org_slug,
                min(devices.count(), max_devices),
                devices.count(),
            )
        return count


@task(
    name="spacedf.tasks.device_downgrade",
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=3,
)
def device_upgrade_task(**kwargs):
    org_slug = kwargs["org_slug"]
    with schema_context(org_slug):
        count = Device.objects.filter(is_deactivated=True).update(is_deactivated=False)
        if count:
            logger.info(
                "Renewal: reactivated %s devices for org %s.",
                count,
                org_slug,
            )
        return count


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

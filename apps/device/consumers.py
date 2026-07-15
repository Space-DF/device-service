"""Device downgrade deactivation logic."""

import logging

from django_tenants.utils import schema_context

from apps.device.models import Device, SpaceDevice

logger = logging.getLogger(__name__)


def deactivate_excess_devices(
    organization_slug: str, limits: dict = None
) -> int:
    limits = limits or {}
    max_devices = limits.get("device.max_count", 10)

    with schema_context(organization_slug):
        active_device_ids = SpaceDevice.objects.filter(
            space__slug_name=organization_slug,
            device__is_deactivated=False,
        ).values_list("device_id", flat=True)

        devices = Device.objects.filter(
            id__in=active_device_ids,
            is_deactivated=False,
        ).order_by("created_at")

        excess_ids = list(
            devices.values_list("id", flat=True)[max_devices:]
        )
        count = (
            Device.objects.filter(id__in=excess_ids).update(
                is_deactivated=True
            )
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

"""Device downgrade deactivation logic.

Keeps the oldest ``FREE_PLAN_MAX_DEVICES`` active devices per org
when a subscription is downgraded to Free. Called by the shared
downgrade consumer.
"""

import logging

from apps.device.constants import DeviceStatus
from apps.device.models import Device, SpaceDevice

logger = logging.getLogger(__name__)

FREE_PLAN_MAX_DEVICES = 10


def deactivate_excess_devices(organization_slug: str) -> int:
    active_device_ids = SpaceDevice.objects.filter(
        space__slug_name=organization_slug,
        device__status=DeviceStatus.ACTIVE,
    ).values_list("device_id", flat=True)

    devices = Device.objects.filter(
        id__in=active_device_ids,
        status=DeviceStatus.ACTIVE,
    ).order_by("created_at")

    excess = devices[FREE_PLAN_MAX_DEVICES:]
    count = excess.update(status=DeviceStatus.DEACTIVATED)
    if count:
        logger.info(
            "Downgrade: deactivated %s excess devices for org %s "
            "(kept %s active out of %s total).",
            count,
            organization_slug,
            min(len(devices), FREE_PLAN_MAX_DEVICES),
            len(devices),
        )
    return count

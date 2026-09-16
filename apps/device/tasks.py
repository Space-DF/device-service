import logging

from common.apps.billing.constants import FeatureCode
from common.celery.tasks import PermanentTaskError, task, tenant_shared_task
from django_tenants.utils import schema_context

from apps.device.models import Device
from apps.device.services.device_subscription_service import (
    reconcile_device_limit,
    send_telemetry_subscription_task,
)

logger = logging.getLogger(__name__)


def _is_unlimited(kwargs, feature_code):
    return feature_code in set(kwargs.get("unlimited_features") or [])


@task(
    name="spacedf.tasks.device_downgrade",
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=3,
)
def device_downgrade_task(**kwargs):
    org_slug = kwargs["org_slug"]
    limits = kwargs.get("limits") or {}
    max_devices = limits.get(FeatureCode.DEVICE_MAX_COUNT)
    if max_devices is None:
        raise PermanentTaskError(
            "device downgrade requires limit %s for org %s"
            % (FeatureCode.DEVICE_MAX_COUNT, org_slug)
        )
    if max_devices < 0:
        raise PermanentTaskError(
            "device downgrade limit %s must be >= 0 for org %s"
            % (FeatureCode.DEVICE_MAX_COUNT, org_slug)
        )

    downgraded_at = kwargs.get("downgraded_at")

    with schema_context(org_slug):
        result = reconcile_device_limit(max_devices, deactivated_at=downgraded_at)
        count = result["deactivated_count"]
        excess_ids = result["suspended_ids"]

    # Keep outside the schema_context - send_task is broker-only,
    # No DB access needed.
    send_telemetry_subscription_task("downgrade", excess_ids, org_slug)
    return count


@task(
    name="spacedf.tasks.device_upgrade",
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=3,
)
def device_upgrade_task(**kwargs):
    org_slug = kwargs["org_slug"]
    limits = kwargs.get("limits") or {}
    max_devices = limits.get(FeatureCode.DEVICE_MAX_COUNT)
    unlimited_devices = _is_unlimited(kwargs, FeatureCode.DEVICE_MAX_COUNT)
    if max_devices is None and not unlimited_devices:
        raise PermanentTaskError(
            "device upgrade requires limit or explicit unlimited feature %s for org %s"
            % (FeatureCode.DEVICE_MAX_COUNT, org_slug)
        )
    if max_devices is not None and max_devices < 0:
        raise PermanentTaskError(
            "device upgrade limit %s must be >= 0 for org %s"
            % (FeatureCode.DEVICE_MAX_COUNT, org_slug)
        )

    with schema_context(org_slug):
        result = reconcile_device_limit(max_devices)
        count = result["reactivated_count"]
        reactivated_ids = result["active_ids"]

    # Cascade reactivation to telemetry entities.
    send_telemetry_subscription_task("upgrade", reactivated_ids, org_slug)
    return count


@tenant_shared_task(name="spacedf.tasks.update_device_location")
def update_device_location(
    device_id: str, latitude: float, longitude: float, bearing: float
):
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        logger.warning(
            f"Device with id={device_id} not found, skipping location update"
        )
        return

    device.location = {
        "latitude": latitude,
        "longitude": longitude,
        "bearing": bearing,
    }
    device.save(update_fields=["location", "updated_at"])

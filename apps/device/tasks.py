import logging

from common.apps.billing.constants import FeatureCode
from common.celery.task_senders import send_subscription_task
from common.celery.tasks import PermanentTaskError, task, tenant_shared_task
from django.utils.dateparse import parse_datetime
from django_tenants.utils import schema_context

from apps.device.models import Device

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
        devices = Device.objects.filter(is_deactivated=False).order_by("created_at")

        excess_ids = list(devices.values_list("id", flat=True)[max_devices:])
        count = (
            Device.objects.filter(id__in=excess_ids, is_deactivated=False).update(
                is_deactivated=True, deactivated_at=downgraded_at
            )
            if excess_ids
            else 0
        )
        if not excess_ids and downgraded_at:
            retry_timestamp = parse_datetime(downgraded_at)
            if retry_timestamp is not None:
                excess_ids = list(
                    Device.objects.filter(
                        is_deactivated=True,
                        deactivated_at=retry_timestamp,
                    ).values_list("id", flat=True)
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

    # Keep outside the schema_context - send_task is broker-only,
    # No DB access needed.
    if excess_ids:
        send_subscription_task(
            service="telemetry",
            lifecycle="downgrade",
            task_name="telemetry_downgrade",
            message={
                "org_slug": org_slug,
                "device_ids": [str(device_id) for device_id in excess_ids],
            },
        )
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
        if max_devices is None:
            reactivated_ids = list(
                Device.objects.order_by("created_at").values_list("id", flat=True)
            )
        else:
            reactivated_ids = list(
                Device.objects.order_by("created_at").values_list("id", flat=True)[
                    :max_devices
                ]
            )
        count = (
            Device.objects.filter(id__in=reactivated_ids, is_deactivated=True).update(
                is_deactivated=False, deactivated_at=None
            )
            if reactivated_ids
            else 0
        )
        if count:
            logger.info(
                "Renewal: reactivated %s devices for org %s.",
                count,
                org_slug,
            )

    # Cascade reactivation to telemetry entities.
    if reactivated_ids:
        send_subscription_task(
            service="telemetry",
            lifecycle="upgrade",
            task_name="telemetry_upgrade",
            message={
                "org_slug": org_slug,
                "device_ids": [str(device_id) for device_id in reactivated_ids],
            },
        )
    return count


@tenant_shared_task(name="spacedf.tasks.update_device_location")
def update_device_location(device_id: str, latitude: float, longitude: float):
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
    }
    device.save(update_fields=["location", "updated_at"])

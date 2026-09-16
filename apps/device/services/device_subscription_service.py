from common.celery.task_senders import send_subscription_task
from django.db import transaction

from apps.device.models import Device


def reconcile_device_limit(max_devices, deactivated_at=None):
    rows = list(
        Device.objects.values_list("id", "is_deactivated").order_by(
            "created_at",
            "id",
        )
    )
    active_limit = len(rows) if max_devices is None else min(len(rows), max_devices)
    active_ids = [device_id for device_id, _ in rows[:active_limit]]
    suspended_ids = [device_id for device_id, _ in rows[active_limit:]]

    active_id_set = set(active_ids)
    suspended_id_set = set(suspended_ids)
    reactivated_ids = [
        device_id
        for device_id, is_deactivated in rows
        if is_deactivated and device_id in active_id_set
    ]
    deactivated_ids = [
        device_id
        for device_id, is_deactivated in rows
        if not is_deactivated and device_id in suspended_id_set
    ]

    reactivated_count = (
        Device.objects.filter(id__in=reactivated_ids, is_deactivated=True).update(
            is_deactivated=False,
            deactivated_at=None,
        )
        if reactivated_ids
        else 0
    )
    deactivated_count = (
        Device.objects.filter(id__in=deactivated_ids, is_deactivated=False).update(
            is_deactivated=True,
            deactivated_at=deactivated_at,
        )
        if deactivated_ids
        else 0
    )

    return {
        "total": len(rows),
        "active_limit": active_limit,
        "active_ids": active_ids,
        "suspended_ids": suspended_ids,
        "reactivated_ids": reactivated_ids,
        "deactivated_ids": deactivated_ids,
        "reactivated_count": reactivated_count,
        "deactivated_count": deactivated_count,
    }


def reactivate_next_suspended_device():
    device = (
        Device.objects.filter(is_deactivated=True).order_by("created_at", "id").first()
    )
    if device is None:
        return None

    device.is_deactivated = False
    device.deactivated_at = None
    device.save(update_fields=["is_deactivated", "deactivated_at", "updated_at"])
    return device.id


def fill_active_slot_after_delete(fill_active_slot, org_slug):
    if not fill_active_slot:
        return

    reactivated_id = reactivate_next_suspended_device()
    if reactivated_id:
        transaction.on_commit(
            lambda: send_telemetry_subscription_task(
                "upgrade",
                [reactivated_id],
                org_slug,
            )
        )


def send_telemetry_subscription_task(lifecycle, device_ids, org_slug):
    if not device_ids:
        return
    send_subscription_task(
        service="telemetry",
        lifecycle=lifecycle,
        task_name=f"telemetry_{lifecycle}",
        message={
            "org_slug": org_slug,
            "device_ids": [str(device_id) for device_id in device_ids],
        },
    )

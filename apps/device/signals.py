import logging

from common.apps.space.models import Space
from common.celery import constants
from common.celery.task_senders import send_task
from django.db import connection
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from apps.device.constants import DeviceStatus
from apps.device.models import Device, SpaceDevice
from apps.device.services.lorawan_cache_service import clear_lorawan_cache
from apps.placement.models import Position

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SpaceDevice)
def handle_device_space_create(sender, instance, created, **kwargs):
    if not created:
        return

    tenant = connection.get_tenant()
    slug_name = getattr(tenant, "slug_name", connection.schema_name)
    Space.objects.filter(slug_name=instance.space.slug_name).update(
        total_devices=F("total_devices") + 1
    )

    send_task(
        name=constants.AUTH_SERVICE_ADD_OR_REMOVE_DEVICE,
        message={
            "slug_name": slug_name,
            "space_slug_name": instance.space.slug_name,
            "type": "add",
        },
    )


@receiver(pre_delete, sender=SpaceDevice)
def handle_device_space_delete(sender, instance, **kwargs):
    Device.objects.filter(id=instance.device.id).update(
        status=DeviceStatus.IN_INVENTORY
    )
    Space.objects.filter(slug_name=instance.space.slug_name).update(
        total_devices=Greatest(F("total_devices") - 1, Value(0))
    )
    tenant = connection.get_tenant()
    slug_name = getattr(tenant, "slug_name", connection.schema_name)
    dev_eui = getattr(getattr(instance.device, "lorawan_device", None), "dev_eui", None)

    clear_lorawan_cache(slug_name, dev_eui)

    send_task(
        name=constants.AUTH_SERVICE_ADD_OR_REMOVE_DEVICE,
        message={
            "slug_name": slug_name,
            "space_slug_name": instance.space.slug_name,
            "type": "remove",
        },
    )

    send_task(
        name="delete_device",
        message={
            "organization_slug_name": slug_name,
            "device_id": str(instance.device.id),
        },
    )


@receiver(pre_delete, sender=Device)
def handle_device_delete(sender, instance, **kwargs):
    tenant = connection.get_tenant()
    slug_name = getattr(tenant, "slug_name", connection.schema_name)
    lorawan_obj = getattr(instance, "lorawan_device", None)
    dev_eui = getattr(lorawan_obj, "dev_eui", None) if lorawan_obj is not None else None

    clear_lorawan_cache(slug_name, dev_eui)


@receiver(post_save, sender=Device)
def handle_device_update(sender, instance, created, **kwargs):
    if created:
        return

    tenant = connection.get_tenant()
    slug_name = getattr(tenant, "slug_name", connection.schema_name)
    lorawan_obj = getattr(instance, "lorawan_device", None)
    dev_eui = getattr(lorawan_obj, "dev_eui", None) if lorawan_obj is not None else None

    clear_lorawan_cache(slug_name, dev_eui)


@receiver(post_delete, sender=SpaceDevice)
def handle_space_device_delete(sender, instance, **kwargs):
    try:
        Position.objects.filter(id=instance.position_id).delete()
    except Exception as e:
        logger.error(f"Failed to delete Position: {str(e)}")

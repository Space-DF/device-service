from common.apps.space.models import Space
from common.celery import constants
from common.celery.task_senders import send_task
from django.db import connection
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.device.constants import DeviceStatus
from apps.device.models import Device, SpaceDevice


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

    send_task(
        name=constants.AUTH_SERVICE_ADD_OR_REMOVE_DEVICE,
        message={
            "slug_name": slug_name,
            "space_slug_name": instance.space.slug_name,
            "type": "remove",
        },
    )

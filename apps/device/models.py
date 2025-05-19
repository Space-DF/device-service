import uuid

from common.apps.space.models import BaseModel, Space
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.device_connector.models import DeviceConnector
from apps.device_model.models import DeviceModel


class Device(BaseModel):
    DEVICE_STATUS = (
        ("active", "Active"),
        ("in_inventory", "In Inventory"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_connector = models.ForeignKey(
        DeviceConnector,
        related_name="devices",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    device_model = models.ForeignKey(
        DeviceModel, related_name="devices", on_delete=models.CASCADE
    )
    status = models.CharField(
        choices=DEVICE_STATUS, max_length=50, default="in_inventory"
    )


class LorawanDevice(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(
        Device, related_name="lorawan_devices", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, unique=True)
    dev_eui = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=255)
    tags = ArrayField(models.CharField(max_length=256))


class SpaceDevice(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug_name = models.SlugField(unique=True)
    description = models.TextField(null=True, blank=True)
    space = models.ForeignKey(
        Space, related_name="space_devices", on_delete=models.CASCADE
    )
    device = models.ForeignKey(
        Device, related_name="space_devices", on_delete=models.CASCADE
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug_name"]),
        ]

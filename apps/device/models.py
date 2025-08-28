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
        Device, related_name="lorawan_device", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, unique=True)
    dev_eui = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=255)
    tags = ArrayField(models.CharField(max_length=256))


class SpaceDevice(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
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
        ]


class DeviceTransformedData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.JSONField(help_text="Actual device transformed data", editable=False)
    timestamp = models.DateTimeField(db_index=True)
    source = models.CharField(max_length=64, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    device_reference = models.CharField(max_length=255, default="unknown")
    # === DENORMALIZED FIELDS FOR PERFORMANCE ===
    device_eui = models.CharField(max_length=255, db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["device_eui", "timestamp"], name="device_timestamp_idx"
            ),
        ]
        ordering = ["-timestamp"]


class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space_device = models.ForeignKey(SpaceDevice, on_delete=models.PROTECT)
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)

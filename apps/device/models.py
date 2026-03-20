import uuid

from common.apps.space.models import BaseModel, Space
from django.db import models

from apps.device.constants import DeviceStatus
from apps.network_server.models import NetworkServer


class Device(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network_server = models.ForeignKey(
        NetworkServer,
        related_name="devices",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    device_model = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        choices=DeviceStatus.choices, default=DeviceStatus.IN_INVENTORY
    )
    is_published = models.BooleanField(default=False)


class LorawanDevice(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(
        Device, related_name="lorawan_device", on_delete=models.CASCADE
    )
    dev_eui = models.CharField(max_length=16, unique=True)
    join_eui = models.CharField(max_length=16, null=True, blank=True)
    app_key = models.CharField(max_length=32, null=True, blank=True)
    claim_code = models.CharField(max_length=100, null=True, blank=True, unique=True)


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
    location = models.JSONField(
        null=True,
        blank=True,
        help_text='Location as JSON: {"latitude": <float>, "longitude": <float>}',
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]


class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space_device = models.ForeignKey(SpaceDevice, on_delete=models.CASCADE)
    started_at = models.DateTimeField(db_index=True)
    is_finished = models.BooleanField(default=False, db_index=True)
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    last_report = models.DateTimeField(
        null=True, blank=True, db_index=True
    )  # Last data point timestamp

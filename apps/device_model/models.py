import uuid

from common.apps.space.models import BaseModel
from django.db import models


class DeviceManufacture(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    portal_url = models.URLField(blank=True, null=True)
    national = models.CharField(max_length=255, blank=True, null=True)


class DeviceModel(BaseModel):
    DEVICE_TYPE = (("lorawan", "LoRaWAN"),)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    alias = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    device_type = models.CharField(
        max_length=255, choices=DEVICE_TYPE, blank=True, null=True
    )
    manufacture = models.ForeignKey(
        DeviceManufacture, related_name="device_models", on_delete=models.CASCADE
    )
    default_config = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["alias"]),
        ]

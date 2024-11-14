import uuid

from common.apps.space.models import BaseModel
from django.db import models


class DeviceType(models.TextChoices):
    TTN_GATEWAY = "ttn_gateway", "TTN Gateway"
    TTN = "ttn", "TTN"
    Chirpstack = "chirpstack", "Chirpstack"
    MQTT = "mqtt", "MQTT"


class DeviceManufacture(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    portal_url = models.URLField(blank=True, null=True)
    national = models.CharField(max_length=255, blank=True, null=True)


class DeviceModel(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    alias = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    manufacture = models.ForeignKey(
        DeviceManufacture, related_name="device_models", on_delete=models.CASCADE
    )
    device_type = models.CharField(
        max_length=50,
        choices=DeviceType.choices,
    )
    default_config = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["alias"]),
        ]

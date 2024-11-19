import uuid

from common.apps.space.models import BaseModel, Space
from django.db import models

from device_model.models import DeviceModel


class Device(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_model = models.ForeignKey(
        DeviceModel, related_name="devices", on_delete=models.CASCADE
    )


class SpaceDevice(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug_name = models.SlugField(unique=True)
    description = models.TextField()
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


class AbstractLorawanDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dev_eui = models.CharField(max_length=255)
    join_eui = models.CharField(max_length=255)
    phy_version = models.CharField(max_length=50)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["dev_eui"]),
        ]

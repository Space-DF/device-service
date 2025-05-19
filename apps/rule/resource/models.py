import uuid

from django.db import models

from apps.device_connector.models import DeviceConnector


class Resource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_connector = models.OneToOneField(
        DeviceConnector, on_delete=models.CASCADE, related_name="device_resource"
    )
    enable = models.BooleanField(default=True)
    name = models.CharField(max_length=255)
    parameters = models.JSONField()
    resource_opts = models.JSONField()
    type = models.CharField(max_length=255)

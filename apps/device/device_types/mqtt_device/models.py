import uuid

from django.db import models

from apps.device.models import Device


class MqttDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(
        Device, related_name="mqtt_device", on_delete=models.CASCADE
    )

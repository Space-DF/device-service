import uuid

from django.db import models

from apps.device.frequency.models import LoraFrequency
from apps.device.models import Device


class TtnGateway(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(
        Device, related_name="ttn_gateway", on_delete=models.CASCADE
    )
    gateway_eui = models.CharField(max_length=255)
    frequency = models.ForeignKey(
        LoraFrequency, related_name="ttn_gateways", on_delete=models.SET_NULL, null=True
    )

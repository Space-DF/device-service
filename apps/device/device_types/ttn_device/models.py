from django.db import models

from apps.device.frequency.models import LoraFrequency
from apps.device.models import AbstractLorawanDevice, Device


class TtnDevice(AbstractLorawanDevice):
    device = models.OneToOneField(
        Device, related_name="ttn_device", on_delete=models.CASCADE
    )
    frequency = models.ForeignKey(
        LoraFrequency, related_name="ttn_devices", on_delete=models.SET_NULL, null=True
    )

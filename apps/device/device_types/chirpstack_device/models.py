from django.db import models

from apps.device.frequency.models import LoraFrequency
from apps.device.models import AbstractLorawanDevice, Device


class ChirpstackDevice(AbstractLorawanDevice):
    device = models.OneToOneField(
        Device, related_name="chipstack_device", on_delete=models.CASCADE
    )
    frequency = models.ForeignKey(
        LoraFrequency,
        related_name="chipstack_devices",
        on_delete=models.SET_NULL,
        null=True,
    )

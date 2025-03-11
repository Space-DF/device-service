from django.db import models

from device.frequency.models import LoraFrequency
from device.models import AbstractLorawanDevice, Device


class ChirpstackDevice(AbstractLorawanDevice):
    device = models.OneToOneField(
        Device, related_name="chirpstack_device", on_delete=models.CASCADE
    )
    frequency = models.ForeignKey(
        LoraFrequency, related_name="chirpstack_devices", on_delete=models.SET_NULL, null=True
    )

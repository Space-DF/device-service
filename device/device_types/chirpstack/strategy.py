from device.device_types.base_strategy import BaseDeviceTypeStrategy

from .serializers import ChirpstackDeviceComponentSerializer


class ChirpstackDeviceTypeStrategy(BaseDeviceTypeStrategy):
    component_related_names = ("chirpstack_device",)
    serializer = ChirpstackDeviceComponentSerializer

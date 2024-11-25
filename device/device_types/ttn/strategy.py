from device.device_types.base_strategy import BaseDeviceTypeStrategy

from .serializers import ReadTtnDeviceComponentSerializer, TtnDeviceComponentSerializer


class TnnDeviceTypeStrategy(BaseDeviceTypeStrategy):
    component_related_names = ("ttn_device",)
    serializer = TtnDeviceComponentSerializer
    read_serializer = ReadTtnDeviceComponentSerializer

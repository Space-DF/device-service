from device.device_types.base_strategy import BaseDeviceTypeStrategy

from .serializers import TtnDeviceComponentSerializer


class TnnDeviceTypeStrategy(BaseDeviceTypeStrategy):
    component_related_names = ("ttn_device",)
    serializer = TtnDeviceComponentSerializer

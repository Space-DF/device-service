from device.device_types.base_strategy import BaseDeviceTypeStrategy

from .serializers import (
    MqttDeviceComponentSerializer,
    ReadMqttDeviceComponentSerializer,
)


class MqttDeviceTypeStrategy(BaseDeviceTypeStrategy):
    component_related_names = ("mqtt_device",)
    serializer = MqttDeviceComponentSerializer
    read_serializer = ReadMqttDeviceComponentSerializer

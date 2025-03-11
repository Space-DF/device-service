from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import (
    BaseDeviceComponentSerializer,
    ReadDeviceComponentSerializer,
)


class MqttDeviceComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("mqtt_device",))


class ReadMqttDeviceComponentSerializer(ReadDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("mqtt_device",))

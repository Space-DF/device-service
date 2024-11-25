from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import BaseDeviceComponentSerializer


class MqttDeviceComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("mqtt_device",))

from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import (
    BaseDeviceComponentSerializer,
    ReadDeviceComponentSerializer,
)


class TtnDeviceComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("ttn_device",))


class ReadTtnDeviceComponentSerializer(ReadDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("ttn_device",))

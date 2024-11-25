from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import (
    BaseDeviceComponentSerializer,
    ReadDeviceComponentSerializer,
)


class ChirpstackDeviceComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("chirpstack_device",))


class ReadChirpstackDeviceComponentSerializer(ReadDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("chirpstack_device",))

from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import BaseDeviceComponentSerializer


class ChirpstackDeviceComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("chirpstack_device",))

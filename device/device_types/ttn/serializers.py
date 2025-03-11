from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import BaseDeviceComponentSerializer


class TtnDeviceComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("ttn_device",))

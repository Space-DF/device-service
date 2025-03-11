from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import (
    BaseDeviceComponentSerializer,
    ReadDeviceComponentSerializer,
)


class TtnGatewayComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("ttn_gateway",))


class ReadTtnGatewayComponentSerializer(ReadDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("ttn_gateway",))

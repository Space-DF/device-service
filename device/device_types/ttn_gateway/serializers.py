from device.components.serializers import ComponentsSerializer
from device.device_types.base_serializers import BaseDeviceComponentSerializer


class TtnGatewayComponentSerializer(BaseDeviceComponentSerializer):
    components = ComponentsSerializer(fields=("ttn_gateway",))

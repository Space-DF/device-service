from device.device_types.base_strategy import BaseDeviceTypeStrategy

from .serializers import (
    ReadTtnGatewayComponentSerializer,
    TtnGatewayComponentSerializer,
)


class TnnGatewayTypeStrategy(BaseDeviceTypeStrategy):
    component_related_names = ("ttn_gateway",)
    serializer = TtnGatewayComponentSerializer
    read_serializer = ReadTtnGatewayComponentSerializer

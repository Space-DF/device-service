from common.serializers.base_serializers import DynamicFieldsSerializer

from .chirpstack_device.serializers import ChirpstackDeviceSerializer
from .mqtt_device.serializers import MqttDeviceSerializer
from .ttn_device.serializers import TtnDeviceSerializer
from .ttn_gateway.serializers import TtnGatewaySerializer


class ComponentsSerializer(DynamicFieldsSerializer):
    chirpstack_device = ChirpstackDeviceSerializer()
    mqtt_device = MqttDeviceSerializer()
    ttn_gateway = TtnGatewaySerializer()
    ttn_device = TtnDeviceSerializer()


COMPONENT_RELATED_NAMES = list(ComponentsSerializer().get_fields().keys())

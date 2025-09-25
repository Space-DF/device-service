from rest_framework.serializers import ModelSerializer

from apps.device_connector.models import DeviceHttpConfig, DeviceMqttConfig


class DeviceHttpConfigSerializer(ModelSerializer):
    class Meta:
        model = DeviceHttpConfig
        fields = ["api_token", "address_url"]


class DeviceMqttConfigSerializer(ModelSerializer):
    class Meta:
        model = DeviceMqttConfig
        fields = ["username", "password", "mqtt_broker"]

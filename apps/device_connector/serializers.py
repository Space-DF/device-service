from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from apps.device_connector.models import (
    DeviceConnector,
    DeviceHttpConfig,
    DeviceMqttConfig,
)


class DeviceHttpConfigSerializer(ModelSerializer):
    class Meta:
        model = DeviceHttpConfig
        fields = ["api_token", "address_url"]


class DeviceMqttConfigSerializer(ModelSerializer):
    class Meta:
        model = DeviceMqttConfig
        fields = ["username", "password", "mqtt_broker"]


class DeviceConnectorSerializer(ModelSerializer):
    deviceHttpConfig = DeviceHttpConfigSerializer(
        source="device_http_config", many=False, required=False, allow_null=True
    )
    deviceMqttConfig = DeviceMqttConfigSerializer(
        source="device_mqtt_config", many=False, required=False, allow_null=True
    )
    status = serializers.CharField(required=False)

    class Meta:
        model = DeviceConnector
        fields = [
            "id",
            "network_server",
            "name",
            "connector_type",
            "status",
            "deviceHttpConfig",
            "deviceMqttConfig",
        ]

    def validate(self, attrs):
        http_config = attrs.get("device_http_config")
        mqtt_config = attrs.get("device_mqtt_config")

        if http_config and mqtt_config:
            raise serializers.ValidationError(
                "Only one of deviceHttpConfig or deviceMqttConfig may be provided."
            )
        if not http_config and not mqtt_config:
            raise serializers.ValidationError(
                "One of deviceHttpConfig or deviceMqttConfig must be provided."
            )

        return attrs

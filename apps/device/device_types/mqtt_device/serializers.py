from rest_framework import serializers
from apps.device.device_types.mqtt_device.models import MqttDevice

class MqttDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MqttDevice
        fields = '__all__'
        extra_kwargs = {"id": {"read_only": True}}

from rest_framework import serializers

from .models import MqttDevice


class MqttDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MqttDevice
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
            "device": {"read_only": True},
        }

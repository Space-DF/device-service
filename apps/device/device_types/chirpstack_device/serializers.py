from rest_framework import serializers

from apps.device.device_types.chirpstack_device.models import ChirpstackDevice


class ChirpstackDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChirpstackDevice
        fields = "__all__"
        extra_kwargs = {"id": {"read_only": True}}

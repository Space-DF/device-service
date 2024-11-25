from rest_framework import serializers

from .models import TtnDevice


class TtnDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TtnDevice
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
            "device": {"read_only": True},
        }

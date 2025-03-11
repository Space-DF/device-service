from rest_framework import serializers

from .models import TtnGateway


class TtnGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = TtnGateway
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
            "device": {"read_only": True},
        }

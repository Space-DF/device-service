from rest_framework import serializers
from apps.device.device_types.ttn_gateway.models import TtnGateway

class TtnGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = TtnGateway
        fields = '__all__'
        extra_kwargs = {"id": {"read_only": True}}

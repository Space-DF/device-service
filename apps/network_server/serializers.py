from rest_framework import serializers

from apps.network_server.models import NetworkServer


class NetworkServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkServer
        fields = "__all__"
        extra_kwargs = {"id": {"read_only": True}}

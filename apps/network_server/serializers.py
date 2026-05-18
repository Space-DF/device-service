from django.conf import settings
from rest_framework import serializers

from apps.network_server.models import NetworkServer


class NetworkServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkServer
        fields = "__all__"
        extra_kwargs = {"id": {"read_only": True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.logo:
            path_url = settings.HOST + "/static/images/network/" + instance.logo
            data["logo"] = path_url
        return data

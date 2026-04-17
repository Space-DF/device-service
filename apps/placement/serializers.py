from rest_framework import serializers

from apps.placement.models import Position


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["x", "y", "z"]

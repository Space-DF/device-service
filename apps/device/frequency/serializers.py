from rest_framework import serializers

from apps.device.frequency.models import LoraFrequency


class LoraFrequencySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoraFrequency
        fields = "__all__"
        extra_kwargs = {"id": {"read_only": True}}
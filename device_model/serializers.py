from rest_framework import serializers

from device_model.models import DeviceManufacture, DeviceModel


class DeviceManufactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceManufacture
        fields = "__all__"
        extra_kwargs = {"id": {"read_only": True}}


class DeviceModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeviceModel
        fields = "__all__"
        extra_kwargs = {"id": {"read_only": True}}

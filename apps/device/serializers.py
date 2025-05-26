from rest_framework.serializers import ModelSerializer

from apps.device.models import Device, LorawanDevice, SpaceDevice


class LorawanDeviceSerializer(ModelSerializer):
    class Meta:
        model = LorawanDevice
        fields = ["name", "dev_eui", "location", "tags"]


class DeviceSerializer(ModelSerializer):
    lorawan_device = LorawanDeviceSerializer(
        source="lorawan_devices", many=False, required=False
    )

    class Meta:
        model = Device
        fields = ["id", "device_connector", "device_model", "status", "lorawan_device"]

    def create(self, validated_data):
        lorawan_data = validated_data.pop("lorawan_devices", None)
        device = Device.objects.create(**validated_data)

        if lorawan_data:
            LorawanDevice.objects.create(device=device, **lorawan_data)

        return device


class SpaceDeviceSerializer(ModelSerializer):
    class Meta:
        model = SpaceDevice
        fields = "__all__"

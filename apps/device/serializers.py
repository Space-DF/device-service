from django.db import transaction
from rest_framework.serializers import ListSerializer, ModelSerializer

from apps.device.models import Device, LorawanDevice, SpaceDevice


class LorawanDeviceSerializer(ModelSerializer):
    class Meta:
        model = LorawanDevice
        fields = ["name", "dev_eui", "location", "tags"]


class MultiDeviceSerializer(ListSerializer):
    @transaction.atomic
    def create(self, validated_data):
        device_objs = []
        lorawan_objs = []

        for item in validated_data:
            lorawan_data = item.pop("lorawan_device", None)
            device_obj = Device(**item)
            lorawan_obj = LorawanDevice(device=device_obj, **lorawan_data)
            device_objs.append(device_obj)
            lorawan_objs.append(lorawan_obj)

        Device.objects.bulk_create(device_objs)
        LorawanDevice.objects.bulk_create(lorawan_objs)

        return device_objs


class DeviceSerializer(ModelSerializer):
    lorawan_device = LorawanDeviceSerializer(many=False, required=False)

    class Meta:
        model = Device
        fields = ["id", "device_connector", "device_model", "status", "lorawan_device"]
        list_serializer_class = MultiDeviceSerializer

    def create(self, validated_data):
        lorawan_data = validated_data.pop("lorawan_device", None)
        device = Device.objects.create(**validated_data)

        if lorawan_data:
            LorawanDevice.objects.create(device=device, **lorawan_data)

        return device

    def update(self, instance, validated_data):
        lorawan_data = validated_data.pop("lorawan_device", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lorawan_data:
            lorawan_instance = getattr(instance, "lorawan_device", None)
            if lorawan_instance:
                lorawan_serializer = LorawanDeviceSerializer(
                    instance=lorawan_instance, data=lorawan_data, partial=True
                )
                lorawan_serializer.is_valid(raise_exception=True)
                lorawan_serializer.save()
            else:
                LorawanDevice.objects.create(device=instance, **lorawan_data)

        return instance


class SpaceDeviceSerializer(ModelSerializer):
    class Meta:
        model = SpaceDevice
        fields = "__all__"

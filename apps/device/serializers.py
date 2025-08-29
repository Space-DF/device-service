from django.db import transaction
from rest_framework import serializers

from apps.device.models import (
    Device,
    DeviceTransformedData,
    LorawanDevice,
    SpaceDevice,
    Trip,
)


class LorawanDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LorawanDevice
        fields = ["name", "dev_eui", "location", "tags"]


class MultiDeviceSerializer(serializers.ListSerializer):
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


class DeviceSerializer(serializers.ModelSerializer):
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


class SpaceDeviceSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)

    class Meta:
        model = SpaceDevice
        fields = ["id", "name", "description", "device"]


class CreateSpaceDeviceSerializer(serializers.ModelSerializer):
    dev_eui = serializers.CharField(max_length=16, write_only=True)

    class Meta:
        model = SpaceDevice
        fields = ["name", "description", "dev_eui"]


class DeviceTransformedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceTransformedData
        fields = "__all__"


class FormatDeviceTransformedDataSerializer(serializers.ModelSerializer):
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    class Meta:
        model = DeviceTransformedData
        fields = ["timestamp", "longitude", "latitude"]

    def get_longitude(self, obj):
        try:
            return obj.data.get("location", {}).get("longitude")
        except Exception:
            return None

    def get_latitude(self, obj):
        try:
            return obj.data.get("location", {}).get("latitude")
        except Exception:
            return None


class TripListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ["id", "space_device", "started_at", "ended_at"]


class TripDetailSerializer(TripListSerializer):
    checkpoints = FormatDeviceTransformedDataSerializer(many=True, read_only=True)

    class Meta(TripListSerializer.Meta):
        fields = TripListSerializer.Meta.fields + ["checkpoints"]

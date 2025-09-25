from common.utils.custom_fields import HexCharField
from django.db import transaction
from rest_framework import serializers

from apps.device.models import (
    Device,
    DeviceTransformedData,
    LorawanDevice,
    SpaceDevice,
    Trip,
)
from apps.network_server.serializers import NetworkServerSerializer


class LorawanDeviceSerializer(serializers.ModelSerializer):
    dev_eui = HexCharField(length=16, unique=True)
    join_eui = HexCharField(length=16)
    app_key = HexCharField(length=32)

    class Meta:
        model = LorawanDevice
        fields = ["join_eui", "dev_eui", "app_key", "claim_code"]


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
        fields = ["id", "network_server", "device_model", "status", "lorawan_device"]
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


class GetDeviceSerializer(DeviceSerializer):
    network_server = NetworkServerSerializer(read_only=True)

    class Meta(DeviceSerializer.Meta):
        model = Device
        fields = "__all__"


class SpaceDeviceSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    latest_checkpoint = serializers.SerializerMethodField()

    class Meta:
        model = SpaceDevice
        fields = ["id", "name", "description", "device", "latest_checkpoint"]

    def get_latest_checkpoint(self, obj):
        if not self.context.get("include_latest_checkpoint"):
            return None
        device = getattr(obj, "device", None)
        if not device or not hasattr(device, "lorawan_device"):
            return None
        dev_eui = getattr(device.lorawan_device, "dev_eui", None)
        if not dev_eui:
            return None
        latest_data = (
            DeviceTransformedData.objects.filter(device_eui=dev_eui)
            .order_by("-timestamp")
            .first()
        )
        if not latest_data:
            return None
        return FormatDeviceCheckpointsSerializer(latest_data).data


class CreateSpaceDeviceSerializer(serializers.ModelSerializer):
    dev_eui = serializers.CharField(max_length=16, write_only=True)

    class Meta:
        model = SpaceDevice
        fields = ["name", "description", "dev_eui"]


class DeviceTransformedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceTransformedData
        fields = "__all__"


class FormatDeviceCheckpointsSerializer(serializers.ModelSerializer):
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
    checkpoints = FormatDeviceCheckpointsSerializer(
        many=True, read_only=True, allow_null=True
    )

    class Meta(TripListSerializer.Meta):
        fields = TripListSerializer.Meta.fields + ["checkpoints"]

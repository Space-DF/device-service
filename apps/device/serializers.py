import logging
from typing import Optional, TypedDict

from common.utils.custom_fields import HexCharField
from django.db import transaction
from rest_framework import serializers

from apps.utils.clients.telemetry_client import TelemetryServiceClient
from apps.device.models import (
    Device,
    DeviceTransformedData,
    LorawanDevice,
    SpaceDevice,
    Trip,
)
from apps.device_model.serializers import DeviceModelSerializer
from apps.network_server.serializers import NetworkServerSerializer

logger = logging.getLogger(__name__)


class Checkpoint(TypedDict):
    """A checkpoint with timestamp and coordinates"""
    timestamp: str
    latitude: float
    longitude: float
    accuracy: float


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


class FormatDeviceSerializer(serializers.ModelSerializer):
    device_id = serializers.UUIDField(read_only=True, source="lorawan_device.id")
    device_profile = serializers.CharField(
        source="device_model.device_type", read_only=True
    )
    space_slug = serializers.CharField()

    class Meta:
        model = Device
        fields = ["id", "device_profile", "device_id", "space_slug"]


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
    device_model = DeviceModelSerializer(read_only=True)

    class Meta(DeviceSerializer.Meta):
        model = Device
        fields = "__all__"


class LatestCheckpointSerializer(serializers.Serializer):
    """Serializer for the latest checkpoint of a device"""
    timestamp = serializers.DateTimeField(help_text="Timestamp of the checkpoint")
    latitude = serializers.FloatField(help_text="Latitude coordinate")
    longitude = serializers.FloatField(help_text="Longitude coordinate")
    accuracy = serializers.FloatField(help_text="Accuracy in meters")


class SpaceDeviceSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    latest_checkpoint = LatestCheckpointSerializer(read_only=True, allow_null=True)

    class Meta:
        model = SpaceDevice
        fields = ["id", "name", "description", "device", "latest_checkpoint"]

    def to_representation(self, instance: SpaceDevice):
        """Override to fetch latest_checkpoint from telemetry service"""
        data = super().to_representation(instance)
        data['latest_checkpoint'] = self._get_latest_checkpoint(instance)
        return data

    def _get_latest_checkpoint(self, obj: SpaceDevice) -> Optional[Checkpoint]:
        """Fetch the latest checkpoint from telemetry service"""
        try:
            organization_slug = obj.space.slug_name
            device_id = str(obj.device.id)

            telemetry_client = TelemetryServiceClient()
            location = telemetry_client.get_last_location(
                device_id=device_id,
                organization_slug=organization_slug
            )

            if location:
                return Checkpoint(
                    timestamp=str(location.timestamp),
                    latitude=location.latitude,
                    longitude=location.longitude,
                    accuracy=location.accuracy
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching latest checkpoint for device {obj.device.id}: {e}")
            return None


class CreateSpaceDeviceSerializer(serializers.ModelSerializer):
    dev_eui = serializers.CharField(max_length=16, write_only=True)

    class Meta:
        model = SpaceDevice
        fields = ["name", "description", "dev_eui"]


class UpdateSpaceDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceDevice
        fields = ["name", "description"]


class DeviceTransformedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceTransformedData
        fields = "__all__"


class CheckpointSerializer(serializers.Serializer):
    """Serializer for location checkpoints from telemetry service"""
    timestamp = serializers.DateTimeField()
    longitude = serializers.FloatField()
    latitude = serializers.FloatField()
    accuracy = serializers.FloatField()


class TripListSerializer(serializers.ModelSerializer):
    space_device_id = serializers.CharField(source="space_device.id", read_only=True)
    device_id = serializers.CharField(source="space_device.device.id", read_only=True)
    device_name = serializers.CharField(source="space_device.name", read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id",
            "space_device_id",
            "device_id",
            "device_name",
            "started_at",
            "is_finished",
            "last_latitude",
            "last_longitude",
            "last_report",
        ]


class TripDetailSerializer(TripListSerializer):
    checkpoints = CheckpointSerializer(
        many=True, read_only=True, allow_null=True,
    )

    class Meta(TripListSerializer.Meta):
        fields = TripListSerializer.Meta.fields + ["checkpoints"]


class TripAnalysisSerializer(serializers.Serializer):
    """Serializer for trip analysis results with telemetry data"""
    id = serializers.UUIDField(read_only=True)
    space_device_id = serializers.UUIDField(read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    is_finished = serializers.BooleanField(read_only=True)
    locations = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    location_count = serializers.IntegerField(read_only=True)

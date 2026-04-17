import logging
from typing import Optional

from common.utils.custom_fields import HexCharField
from common.utils.telemetry_client import TelemetryServiceClient
from common.utils.tranformer_client import TranformerServiceClient
from django.db import transaction
from rest_framework import serializers

from apps.building.models import Area, Floor
from apps.building.serializers import AreaSerializer, FloorSerializer
from apps.device.constants import DeviceStatus
from apps.device.models import Device, LorawanDevice, SpaceDevice, Trip
from apps.facility.models import Facility
from apps.facility.serializers import FacilitySerializer
from apps.network_server.serializers import NetworkServerSerializer
from apps.placement.serializers import PositionSerializer

logger = logging.getLogger(__name__)


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
    space_slug = serializers.CharField()

    class Meta:
        model = Device
        fields = ["id", "device_id", "device_model", "space_slug", "is_published"]


class DeviceSerializer(serializers.ModelSerializer):
    lorawan_device = LorawanDeviceSerializer(many=False, required=False)

    class Meta:
        model = Device
        fields = [
            "id",
            "network_server",
            "device_model",
            "status",
            "lorawan_device",
            "is_published",
        ]
        list_serializer_class = MultiDeviceSerializer

    def to_representation(self, instance):
        data = super().to_representation(instance)
        device_profile = None
        if instance.device_model:
            try:
                client = TranformerServiceClient()
                device_profile = client.get_device_model(str(instance.device_model))
            except Exception as e:
                logger.error(
                    f"Failed to fetch device model for {instance.id}: {str(e)}",
                    exc_info=True,
                )
        data["device_profile"] = device_profile
        return data

    def create(self, validated_data):
        lorawan_data = validated_data.pop("lorawan_device", None)
        try:
            device = Device.objects.create(**validated_data)
            logger.info(f"Device created successfully with ID: {device.id}")

            if lorawan_data:
                LorawanDevice.objects.create(device=device, **lorawan_data)
                logger.info(f"LoRaWAN device created for device {device.id}")

            return device
        except Exception as e:
            logger.error(f"Failed to create device: {str(e)}", exc_info=True)
            raise

    def update(self, instance, validated_data):
        lorawan_data = validated_data.pop("lorawan_device", None)

        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            logger.info(f"Device {instance.id} updated successfully")
        except Exception as e:
            logger.error(
                f"Failed to update device {instance.id}: {str(e)}", exc_info=True
            )
            raise

        if lorawan_data:
            try:
                lorawan_instance = getattr(instance, "lorawan_device", None)
                if lorawan_instance:
                    lorawan_serializer = LorawanDeviceSerializer(
                        instance=lorawan_instance, data=lorawan_data, partial=True
                    )
                    lorawan_serializer.is_valid(raise_exception=True)
                    lorawan_serializer.save()
                    logger.info(f"LoRaWAN device updated for device {instance.id}")
                else:
                    LorawanDevice.objects.create(device=instance, **lorawan_data)
                    logger.info(f"New LoRaWAN device created for device {instance.id}")
            except Exception as e:
                logger.error(
                    f"Failed to update LoRaWAN device for {instance.id}: {str(e)}",
                    exc_info=True,
                )
                raise

        return instance


class GetDeviceSerializer(DeviceSerializer):
    network_server = NetworkServerSerializer(read_only=True)

    class Meta(DeviceSerializer.Meta):
        model = Device
        fields = "__all__"


class SpaceDeviceSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    facility = FacilitySerializer(read_only=True)
    floor = FloorSerializer(read_only=True)
    area = AreaSerializer(read_only=True)
    position = PositionSerializer(read_only=True)

    class Meta:
        model = SpaceDevice
        fields = [
            "id",
            "name",
            "description",
            "device",
            "facility",
            "floor",
            "area",
            "position",
        ]

    def validate(self, data):
        provided_fields = [
            field
            for field in [data.get("facility"), data.get("floor"), data.get("area")]
            if field is not None
        ]

        if len(provided_fields) not in [0, 1]:
            raise serializers.ValidationError(
                "Exactly one of facility, floor, area must be provided."
            )
        return data

    def to_representation(self, instance: SpaceDevice):
        """Override to fetch device_properties from telemetry service"""
        data = super().to_representation(instance)
        data["device_properties"] = self._get_device_properties(instance)
        return data

    def _get_device_properties(self, obj: SpaceDevice) -> Optional[dict]:
        """Fetch all device properties from telemetry service"""
        try:
            space_slug = obj.space.slug_name
            device_id = str(obj.device.id)
            logger.debug(
                f"Fetching device properties for device {device_id} in space {space_slug}"
            )

            organization_slug = ""
            request = self.context.get("request")
            if request and hasattr(request, "tenant"):
                organization_slug = request.tenant.slug_name

            telemetry_client = TelemetryServiceClient()
            device_props = telemetry_client.get_device_properties(
                device_id, organization_slug, space_slug
            )

            logger.info(
                f"Successfully fetched device properties for device {device_id}"
            )
            return device_props if device_props else None
        except Exception as e:
            logger.error(
                f"Error fetching device properties for device {obj.device.id}: {str(e)}"
            )
            return None


class CreateSpaceDeviceSerializer(SpaceDeviceSerializer):
    dev_eui = serializers.CharField(max_length=16, write_only=True)
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.all(), required=False, allow_null=True
    )
    floor = serializers.PrimaryKeyRelatedField(
        queryset=Floor.objects.all(), required=False, allow_null=True
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), required=False, allow_null=True
    )
    position = PositionSerializer(required=False, allow_null=True)

    class Meta:
        model = SpaceDevice
        fields = [
            "name",
            "description",
            "dev_eui",
            "facility",
            "floor",
            "area",
            "position",
        ]

    @transaction.atomic
    def create(self, validated_data):
        dev_eui = validated_data.pop("dev_eui").lower()
        position_data = validated_data.pop("position", None)
        device = Device.objects.filter(lorawan_device__dev_eui=dev_eui).first()

        if not device:
            raise serializers.ValidationError(
                f"Device with dev_eui = {dev_eui} not in the organization"
            )

        if device.status == DeviceStatus.ACTIVE:
            raise serializers.ValidationError(
                f"Device with dev_eui = {dev_eui} not in the inventory"
            )

        device.status = DeviceStatus.ACTIVE
        device.save()

        space_device = SpaceDevice.objects.create(device=device, **validated_data)
        if position_data:
            position_serializer = PositionSerializer(data=position_data)
            position_serializer.is_valid(raise_exception=True)
            space_device.position = position_serializer.save()
            space_device.save(update_fields=["position"])

        return space_device


class UpdateSpaceDeviceSerializer(SpaceDeviceSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.all(), required=False, allow_null=True
    )
    floor = serializers.PrimaryKeyRelatedField(
        queryset=Floor.objects.all(), required=False, allow_null=True
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), required=False, allow_null=True
    )
    position = PositionSerializer(required=False, allow_null=True)

    class Meta:
        model = SpaceDevice
        fields = [
            "name",
            "description",
            "facility",
            "floor",
            "area",
            "position",
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        position_data = validated_data.pop("position", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if position_data is not None:
            if instance.position:
                position_serializer = PositionSerializer(
                    instance.position, data=position_data, partial=True
                )
            else:
                position_serializer = PositionSerializer(data=position_data)

            position_serializer.is_valid(raise_exception=True)
            instance.position = position_serializer.save()

        instance.save()
        return instance


class FormatSpaceDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceDevice
        fields = ["id", "name", "description"]


class CheckpointSerializer(serializers.Serializer):
    """Serializer for location checkpoints from telemetry service"""

    timestamp = serializers.DateTimeField()
    longitude = serializers.FloatField()
    latitude = serializers.FloatField()


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
        many=True,
        read_only=True,
        allow_null=True,
    )

    class Meta(TripListSerializer.Meta):
        fields = TripListSerializer.Meta.fields + ["checkpoints"]

import logging
from functools import cached_property

from common.utils.custom_fields import HexCharField
from django.db import transaction
from rest_framework import serializers

from apps.building.models import Area, Building, Floor
from apps.building.serializers import (
    AreaSerializer,
    BuildingSerializer,
    FloorSerializer,
)
from apps.device.constants import DeviceStatus
from apps.device.models import APIDevice, Device, LorawanDevice, SpaceDevice, Trip
from apps.device.services.entity_properties_context import (
    _resolve_entity_properties_from_context,
)
from apps.device.services.nested_device_handlers import get_nested_device_handlers
from apps.facility.models import Facility
from apps.facility.serializers import FacilitySerializer
from apps.network_server.models import NetworkServer
from apps.network_server.serializers import NetworkServerSerializer
from apps.placement.models import Position
from apps.placement.serializers import PositionSerializer

logger = logging.getLogger(__name__)


class LorawanDeviceSerializer(serializers.ModelSerializer):
    dev_eui = HexCharField(length=16, unique=True)
    join_eui = HexCharField(length=16)
    app_key = HexCharField(length=32)
    network_server = serializers.PrimaryKeyRelatedField(
        queryset=NetworkServer.objects.all()
    )

    class Meta:
        model = LorawanDevice
        fields = ["join_eui", "dev_eui", "app_key", "network_server"]


class ReadLorawanDeviceSerializer(LorawanDeviceSerializer):
    network_server = NetworkServerSerializer(read_only=True)


class APIDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIDevice
        fields = ["serial_number"]


class MultiDeviceSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        handlers = get_nested_device_handlers()
        valid_items = []
        duplicated = []
        validation_error = []
        request_identifiers = {handler.relation: set() for handler in handlers}
        existing_identifiers = {
            handler.relation: handler.get_existing_identifiers(
                self._handler_identifiers(handler, data)
            )
            for handler in handlers
        }

        for item in data:
            identifiers = {
                handler.relation: handler.get_identifier(item)
                for handler in handlers
                if handler.get_identifier(item)
            }
            primary_identifier = next(iter(identifiers.values()), None)

            if not identifiers:
                validation_error.append(None)
                continue

            has_duplicate = False
            for relation, identifier in identifiers.items():
                if identifier in request_identifiers[relation]:
                    duplicated.append(identifier)
                    has_duplicate = True
                    break
                if identifier in existing_identifiers[relation]:
                    duplicated.append(identifier)
                    has_duplicate = True
                    break
                request_identifiers[relation].add(identifier)
            if has_duplicate:
                continue

            serializer = self.child.__class__(
                data=item,
                context=self.context,
            )

            if serializer.is_valid():
                valid_items.append(serializer.validated_data)
                continue

            validation_error.append(primary_identifier)

        self._total_failed = len(duplicated) + len(validation_error)
        self._failed_data = {
            "duplicated": duplicated,
            "validation_errors": validation_error,
        }

        return valid_items

    def _handler_identifiers(self, handler, items):
        identifiers = []
        for item in items:
            identifier = handler.get_identifier(item)
            if identifier:
                identifiers.append(identifier)
        return identifiers

    @transaction.atomic
    def create(self, validated_data):
        handlers = get_nested_device_handlers()
        device_objs = []
        nested_objs = {handler.relation: [] for handler in handlers}

        for item in validated_data:
            nested_data = {
                handler.relation: handler.pop_data(item) for handler in handlers
            }
            device_obj = Device(**item)
            device_objs.append(device_obj)
            for handler in handlers:
                data = nested_data.get(handler.relation)
                if data:
                    nested_objs[handler.relation].append(
                        handler.build_instance(device_obj, data)
                    )

        Device.objects.bulk_create(device_objs)
        for handler in handlers:
            if nested_objs[handler.relation]:
                handler.model_class.objects.bulk_create(nested_objs[handler.relation])

        return device_objs


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    bearing = serializers.FloatField(required=False, allow_null=True)


class FormatDeviceSerializer(serializers.ModelSerializer):
    device_id = serializers.UUIDField(read_only=True, source="lorawan_device.id")
    space_slug = serializers.CharField()
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "device_id",
            "device_model",
            "space_slug",
            "is_deactivated",
            "is_published",
            "cells",
            "location",
        ]


class DeviceSerializer(serializers.ModelSerializer):
    lorawan_device = LorawanDeviceSerializer(many=False, required=False)
    api_device = APIDeviceSerializer(many=False, required=False)
    location = LocationSerializer(required=False, allow_null=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "device_model",
            "claim_code",
            "status",
            "lorawan_device",
            "api_device",
            "is_published",
            "is_deactivated",
            "cells",
            "location",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "status": {"read_only": True},
            "is_deactivated": {"read_only": True},
        }
        list_serializer_class = MultiDeviceSerializer

    def to_representation(self, instance):
        data = super().to_representation(instance)
        device_profile = None
        if instance.device_model:
            device_model_id = str(instance.device_model)
            profiles_by_model_id = self.context.get("device_profiles_by_model_id", {})
            try:
                device_profile = profiles_by_model_id.get(device_model_id)
            except Exception as e:
                logger.error(
                    f"Failed to fetch device model for {instance.id}: {str(e)}",
                    exc_info=True,
                )
        data["device_profile"] = device_profile
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        handlers_by_relation = {
            handler.relation: handler for handler in get_nested_device_handlers()
        }
        input_relations = [key for key in attrs.keys() if key in handlers_by_relation]

        if len(input_relations) > 1:
            raise serializers.ValidationError("Provide only one device type.")
        if self.instance is None and not input_relations:
            raise serializers.ValidationError("Provide exactly one device type.")

        return attrs

    def create(self, validated_data):
        handler = self._get_input_handler(validated_data)
        nested_data = handler.pop_data(validated_data)

        try:
            with transaction.atomic():
                device = Device.objects.create(**validated_data)
                handler.create(device, nested_data)
                logger.info(f"{handler.label} created for device {device.id}")

            logger.info(f"Device created successfully with ID: {device.id}")
            return device
        except Exception as e:
            logger.error(f"Failed to create device: {str(e)}", exc_info=True)
            raise

    def update(self, instance, validated_data):
        handler = self._get_input_handler(validated_data)
        nested_data = handler.pop_data(validated_data) if handler else None

        try:
            with transaction.atomic():
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                instance.save()
                if handler:
                    handler.update(instance, nested_data)
            logger.info("Device %s updated successfully", instance.id)
        except Exception:
            logger.exception("Failed to update device %s", instance.id)
            raise
        return instance

    def _get_input_handler(self, validated_data):
        handlers_by_relation = {
            handler.relation: handler for handler in get_nested_device_handlers()
        }
        relation = next(
            (key for key in validated_data.keys() if key in handlers_by_relation),
            None,
        )
        if not relation:
            return None
        return handlers_by_relation[relation]


class GetDeviceSerializer(DeviceSerializer):
    lorawan_device = ReadLorawanDeviceSerializer(read_only=True)

    class Meta(DeviceSerializer.Meta):
        model = Device
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        organization_slug = getattr(tenant, "slug_name", "")
        telemetry_data = _resolve_entity_properties_from_context(
            self.context,
            instance,
            organization_slug,
        )
        data["device_properties"] = telemetry_data["device_properties"]
        return data


class SpaceDeviceSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    facility = FacilitySerializer(read_only=True)
    floor = FloorSerializer(read_only=True)
    building = BuildingSerializer(read_only=True)
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
            "building",
            "floor",
            "area",
            "position",
        ]

    @cached_property
    def organization_slug(self) -> str:
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        return getattr(tenant, "slug_name", "") or ""

    def validate(self, data):
        provided_fields = [
            field
            for field in [
                data.get("facility"),
                data.get("floor"),
                data.get("area"),
                data.get("building"),
            ]
            if field is not None
        ]

        if len(provided_fields) not in [0, 1]:
            raise serializers.ValidationError(
                "Exactly one of facility, floor, area, building must be provided."
            )
        return data

    def to_representation(self, instance):
        if isinstance(instance, Device):
            return self._to_public_representation(instance)

        data = super().to_representation(instance)
        telemetry_data = _resolve_entity_properties_from_context(
            self.context,
            instance,
            self.organization_slug,
        )
        data["device_properties"] = telemetry_data["device_properties"]
        data["entities"] = telemetry_data["entities"]
        return data

    def _to_public_representation(self, instance: Device) -> dict:
        device_id = str(instance.id)
        telemetry_data = _resolve_entity_properties_from_context(
            self.context,
            instance,
            self.organization_slug,
        )

        return {
            "id": device_id,
            "name": "Public device",
            "device": DeviceSerializer(instance, context=self.context).data,
            "device_properties": telemetry_data["device_properties"],
            "entities": telemetry_data["entities"],
        }


class CreateSpaceDeviceSerializer(SpaceDeviceSerializer):
    dev_eui = serializers.CharField(max_length=16, write_only=True)
    building = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), required=False, allow_null=True
    )
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
            "building",
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
                "This device does not belong to the organization."
            )

        if device.status == DeviceStatus.ACTIVE:
            raise serializers.ValidationError(
                "This device is already active and cannot be added from inventory."
            )

        if device.is_published:
            raise serializers.ValidationError(
                "This device has been published and cannot be added to space."
            )

        device.status = DeviceStatus.ACTIVE
        device.save()

        if position_data:
            position_serializer = PositionSerializer(data=position_data)
            position_serializer.is_valid(raise_exception=True)
            validated_data["position"] = position_serializer.save()

        space_device = SpaceDevice.objects.create(device=device, **validated_data)

        return space_device


class UpdateSpaceDeviceSerializer(SpaceDeviceSerializer):
    facility = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.all(), required=False, allow_null=True
    )
    building = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), required=False, allow_null=True
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
            "building",
            "facility",
            "floor",
            "area",
            "position",
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        has_position = "position" in validated_data
        position_data = validated_data.pop("position", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if not has_position:
            instance.save()
            return instance

        if position_data is None:
            old_position_id = instance.position_id
            instance.position = None
            instance.save()
            if old_position_id:
                Position.objects.filter(
                    id=old_position_id,
                    position_devices__isnull=True,
                ).delete()
            return instance

        serializer = (
            PositionSerializer(instance.position, data=position_data, partial=True)
            if instance.position
            else PositionSerializer(data=position_data)
        )

        serializer.is_valid(raise_exception=True)
        instance.position = serializer.save()

        instance.save()
        return instance


class MultiSpaceDevicePositionSerializer(serializers.ListSerializer):
    def update(self, instances, validated_data):
        instance_mapping = {instance.id: instance for instance in instances}
        update_devices = []
        create_positions = []
        update_positions = {}
        old_position_ids = []

        for item in validated_data:
            instance = instance_mapping[item["id"]]
            position_data = item.get("position")

            if position_data is None:
                if instance.position_id:
                    old_position_ids.append(instance.position_id)
                instance.position = None
                update_devices.append(instance)
                continue

            position = instance.position or Position()
            for attr, value in position_data.items():
                setattr(position, attr, value)

            if instance.position_id:
                update_positions[position.id] = position
            else:
                create_positions.append(position)

            instance.position = position
            update_devices.append(instance)

        if create_positions:
            Position.objects.bulk_create(create_positions)

        if update_positions:
            Position.objects.bulk_update(
                update_positions.values(),
                ["x", "y", "z", "updated_at"],
            )

        if update_devices:
            SpaceDevice.objects.bulk_update(
                update_devices,
                ["position", "updated_at"],
            )

        if old_position_ids:
            Position.objects.filter(
                id__in=old_position_ids,
                position_devices__isnull=True,
            ).delete()

        return update_devices


class UpdateSpaceDevicePositionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    position = PositionSerializer(allow_null=True)

    class Meta:
        model = SpaceDevice
        fields = ["id", "position"]
        list_serializer_class = MultiSpaceDevicePositionSerializer


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

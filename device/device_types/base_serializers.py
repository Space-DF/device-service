from common.serializers.base_serializers import DynamicModelSerializer
from django.db import models

from device.components.serializers import ComponentsSerializer
from device.models import Device
from device_model.serializers import DeviceModelSerializer


class CreateDevicecomponentsSerializerMixin:
    def create(self, validated_data: dict):
        components_data = validated_data.pop("components", None)

        device = Device.objects.create(**validated_data)

        if components_data:
            for related_name, data in components_data.items():
                if data:
                    related_model: models.Model = device._meta.get_field(
                        related_name
                    ).related_model
                    related_model.objects.create(device=device, **data)

        return device


class BaseDeviceComponentSerializer(
    CreateDevicecomponentsSerializerMixin, DynamicModelSerializer
):
    components = ComponentsSerializer()

    class Meta:
        model = Device
        fields = "__all__"
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def to_representation(self, instance):
        components_data = {}
        components_serializer: ComponentsSerializer = self.fields.pop(
            "components", None
        )
        if components_serializer:
            components_data = components_serializer.to_representation(instance)
        data = super().to_representation(instance)
        if components_data:
            data["components"] = components_data
        return data

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class DeviceComponentSerializer(BaseDeviceComponentSerializer):
    pass


class ReadDeviceComponentSerializer(BaseDeviceComponentSerializer):
    device_model = DeviceModelSerializer(read_only=True)
    components = ComponentsSerializer(read_only=True)

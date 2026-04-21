from common.apps.upload_file.service import get_presigned_url
from django.conf import settings
from rest_framework import serializers

from apps.building.models import Area, Building, Floor


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ["id", "name", "description", "location", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "level",
            "scene_asset",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.scene_asset:
            data["url_scene_asset"] = get_presigned_url(
                settings.AWS_S3.get("AWS_STORAGE_BUCKET_NAME"),
                f"uploads/{instance.scene_asset}",
            )
        return data


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = [
            "id",
            "name",
            "description",
            "area_type",
            "scene_asset",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.scene_asset:
            data["url_scene_asset"] = get_presigned_url(
                settings.AWS_S3.get("AWS_STORAGE_BUCKET_NAME"),
                f"uploads/{instance.scene_asset}",
            )
        return data

from common.apps.upload_file.service import get_presigned_url
from django.conf import settings
from rest_framework import serializers

from apps.facility.models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "description",
            "location",
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

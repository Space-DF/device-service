import uuid

from common.apps.space.models import BaseModel, Space
from django.db import models


class Building(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    space = models.ForeignKey(
        Space, related_name="space_buildings", on_delete=models.CASCADE
    )
    location = models.JSONField(
        null=True,
        blank=True,
        help_text='Location as JSON: {"latitude": <float>, "longitude": <float>}',
    )
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["space"]),
        ]


class Floor(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    building = models.ForeignKey(
        Building, related_name="building_floors", on_delete=models.CASCADE
    )
    level = models.IntegerField(default=1)
    scene_asset = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["building"]),
        ]


class Area(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    floor = models.ForeignKey(
        Floor, related_name="floor_areas", on_delete=models.CASCADE
    )
    area_type = models.CharField(
        max_length=50,
    )
    scene_asset = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["floor"]),
            models.Index(fields=["area_type"]),
        ]

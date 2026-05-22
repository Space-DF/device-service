import uuid

from common.apps.space.models import BaseModel, Space
from django.db import models


class Facility(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    space = models.ForeignKey(
        Space, related_name="space_facilities", on_delete=models.CASCADE
    )
    location = models.JSONField(
        null=True,
        blank=True,
        help_text='Location as JSON: {"latitude": <float>, "longitude": <float>}',
    )
    description = models.TextField(null=True, blank=True)
    scene_asset = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["space"]),
        ]

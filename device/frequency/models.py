import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class LoraFrequency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    frequency = models.CharField(max_length=255)
    phy_versions = ArrayField(models.CharField(max_length=50), blank=True, default=list)

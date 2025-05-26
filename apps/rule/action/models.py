import uuid

from django.db import models


class Action(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enable = models.BooleanField(default=True)
    name = models.CharField(max_length=255, unique=True)
    parameters = models.JSONField()
    resource_opts = models.JSONField()
    type = models.CharField(max_length=255)

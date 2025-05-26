import uuid

from django.db import models

from apps.rule.action.models import Action
from apps.rule.resource.models import Resource


class Definition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.OneToOneField(
        Resource, on_delete=models.CASCADE, related_name="device_rule"
    )
    rule_id = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, related_name="device_rule"
    )
    sql = models.CharField(max_length=255)

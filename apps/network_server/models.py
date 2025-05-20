import uuid

from common.models.base_model import BaseModel
from django.contrib.postgres.fields import ArrayField
from django.db import models


class NetworkServer(BaseModel):
    TYPE_CONNECT = (
        ("mqtt_broker", "MQTT Broker"),
        ("http_server", "HTTP Server"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    logo = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=255)
    type_connect = ArrayField(
        models.CharField(max_length=50, choices=TYPE_CONNECT, null=True),
        blank=True,
        default=list,
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

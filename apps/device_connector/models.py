import uuid

from django.db import models

from apps.network_server.models import NetworkServer


class DeviceHttpConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network_server = models.ForeignKey(
        NetworkServer,
        related_name="device_http_configs",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    api_token = models.CharField(max_length=255)
    address_url = models.CharField(max_length=255)


class DeviceMqttConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network_server = models.ForeignKey(
        NetworkServer,
        related_name="device_mqtt_configs",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    mqtt_broker = models.CharField(max_length=255)

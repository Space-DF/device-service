import uuid

from common.models.base_model import BaseModel
from django.db import models

from apps.network_server.models import NetworkServer


class DeviceConnector(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    network_server = models.ForeignKey(
        NetworkServer, on_delete=models.CASCADE, related_name="device_connector"
    )
    name = models.CharField(max_length=255, unique=True)
    connector_type = models.CharField(max_length=255)
    status = models.CharField(max_length=255)


class DeviceHttpConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_connector = models.OneToOneField(
        DeviceConnector, on_delete=models.CASCADE, related_name="device_http_config"
    )
    api_token = models.CharField(max_length=255)
    address_url = models.CharField(max_length=255)


class DeviceMqttConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_connector = models.OneToOneField(
        DeviceConnector, on_delete=models.CASCADE, related_name="device_mqtt_config"
    )
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    mqtt_broker = models.CharField(max_length=255)

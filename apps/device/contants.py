from django.db import models


class DeviceStatus(models.TextChoices):
    ACTIVE = "active"
    IN_INVENTORY = "in_inventory"

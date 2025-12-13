from django.db import models


class KeyFeature(models.TextChoices):
    WATER_LEVEL_SENSOR = "water_level_sensor"
    MULTI_SENSOR_TRACKER = "multi_sensor_tracker"

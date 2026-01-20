from django.db import models


class KeyFeature(models.TextChoices):
    WATER_DEPTH_TYPE = "water_depth"
    LOCATION_TYPE = "location"

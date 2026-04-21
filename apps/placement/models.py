import uuid

from common.apps.space.models import BaseModel
from django.db import models


class Position(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    x = models.FloatField(default=0.0)
    y = models.FloatField(default=0.0)
    z = models.FloatField(default=0.0)

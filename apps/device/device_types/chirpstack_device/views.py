from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets

from apps.device.device_types.chirpstack_device.models import ChirpstackDevice
from apps.device.device_types.chirpstack_device.serializers import (
    ChirpstackDeviceSerializer,
)


class ChirpstackDeviceViewSet(viewsets.ModelViewSet):
    queryset = ChirpstackDevice.objects.all()
    pagination_class = BasePagination
    serializer_class = ChirpstackDeviceSerializer

from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets

from apps.device.device_types.ttn_device.models import TtnDevice
from apps.device.device_types.ttn_device.serializers import TtnDeviceSerializer


class TtnDeviceViewSet(viewsets.ModelViewSet):
    queryset = TtnDevice.objects.all()
    pagination_class = BasePagination
    serializer_class = TtnDeviceSerializer

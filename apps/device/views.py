from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets

from apps.device.models import Device
from apps.device.serializers import DeviceSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    pagination_class = BasePagination

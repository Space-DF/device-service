from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.device.models import Device, SpaceDevice
from apps.device.serializers import DeviceSerializer, SpaceDeviceSerializer
from apps.device_model.views import UseTenantFromRequestMixin


class DeviceViewSet(UseTenantFromRequestMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["created_at"]
    search_fields = ["status"]


class SpaceDeviceViewSet(viewsets.ModelViewSet):
    queryset = SpaceDevice.objects.all()
    serializer_class = SpaceDeviceSerializer
    pagination_class = BasePagination

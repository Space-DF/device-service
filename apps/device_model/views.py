from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.device_model.models import DeviceManufacture, DeviceModel
from apps.device_model.serializers import (
    DeviceManufactureSerializer,
    DeviceModelSerializer,
)


class DeviceManufactureViewSet(viewsets.ModelViewSet):
    queryset = DeviceManufacture.objects.all()
    serializer_class = DeviceManufactureSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name"]


class DeviceModelViewSet(viewsets.ModelViewSet):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name", "alias"]

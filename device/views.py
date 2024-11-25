from uuid import UUID

from common.pagination.base_pagination import BasePagination
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from device.components.serializers import COMPONENT_RELATED_NAMES
from device.device_types.base_serializers import (
    DeviceComponentSerializer,
    ReadDeviceComponentSerializer,
)
from device.device_types.base_strategy import BaseDeviceTypeStrategy
from device.device_types.factory import DeviceTypeStrategyFactory
from device_model.models import DeviceModel

from .models import Device


class DeviceListCreateAPIView(ListCreateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceComponentSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["created_at"]
    search_fields = ["device_model__name", "device_model__alias"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ReadDeviceComponentSerializer
        elif self.request.method == "POST":
            return DeviceComponentSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return self.queryset.select_related("device_model", *COMPONENT_RELATED_NAMES)

    def get_device_type(self):
        try:
            device_model = DeviceModel.objects.get(
                id=self.request.data.get("device_model")
            )
            return device_model.device_type
        except DeviceModel.DoesNotExist:
            raise ValidationError("Device model does not exist.")

    def get_device_type_strategy(self):
        device_type = self.get_device_type()
        return DeviceTypeStrategyFactory.get_strategy(device_type)

    def create(self, request, *args, **kwargs):
        try:
            strategy_class: BaseDeviceTypeStrategy = self.get_device_type_strategy()
            strategy_instance = strategy_class()
            data = strategy_instance.create_device(self.request.data)
            return Response(data.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class DeviceRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = DeviceComponentSerializer
    queryset = Device.objects.all()

    def get_device_type(self, device_id: UUID):
        try:
            device = Device.objects.select_related("device_model").get(id=device_id)
            return device.device_model.device_type
        except Device.DoesNotExist:
            raise ValidationError("Device does not exist.")

    def get_device_type_strategy(self):
        device_type = self.get_device_type(self.kwargs["pk"])
        return DeviceTypeStrategyFactory.get_strategy(device_type)

    def retrieve(self, request, *args, **kwargs):
        try:
            strategy_class: BaseDeviceTypeStrategy = self.get_device_type_strategy()
            component_related_names: tuple = strategy_class.component_related_names
            device = self.queryset.select_related(
                "device_model", *component_related_names
            ).get(id=kwargs["pk"])
            serializer = strategy_class.read_serializer(device)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

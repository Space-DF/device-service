from common.pagination.base_pagination import BasePagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

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

    @swagger_auto_schema(
        method="post",
        request_body=DeviceSerializer(many=True),
        responses={201: DeviceSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="bulk-create")
    def create_multi_device(self, request):
        serializer = DeviceSerializer(
            data=request.data, many=True, context=self.get_serializer_context()
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        devices = serializer.save()
        return Response(
            DeviceSerializer(devices, many=True).data, status=status.HTTP_201_CREATED
        )


class SpaceDeviceViewSet(viewsets.ModelViewSet):
    queryset = SpaceDevice.objects.all()
    serializer_class = SpaceDeviceSerializer
    pagination_class = BasePagination

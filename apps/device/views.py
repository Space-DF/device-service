from common.apps.space.models import Space
from common.pagination.base_pagination import BasePagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError
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

    def get_queryset(self):
        return Device.objects.select_related("lorawan_device").all()

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


class ListCreateSpaceDeviceViewSet(generics.ListCreateAPIView):
    serializer_class = SpaceDeviceSerializer
    pagination_class = BasePagination

    def _get_space(self):
        slug_name = self.request.headers.get("X-Space")
        if not slug_name:
            raise ParseError("X-Space header is required.")
        try:
            return Space.objects.get(slug_name=slug_name)
        except Space.DoesNotExist:
            raise NotFound(f"Space with slug_name='{slug_name}' not found.")

    def get_queryset(self):
        space = self._get_space()
        return SpaceDevice.objects.filter(space=space).select_related("space", "device")

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        space = self._get_space()
        dev_eui = serializer.validated_data.pop("dev_eui")
        device = Device.objects.filter(lorawan_device__dev_eui=dev_eui).first()
        if not device:
            return Response(
                {
                    "detail": f"Device with dev_eui = {dev_eui} not found in the organization"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if device.status == "active":
            return Response(
                {
                    "detail": f"Device with dev_eui = {dev_eui} not found in the inventory"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        device.status = "active"
        device.save()
        serializer.save(space=space, device=device)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DeleteSpaceDeviceViewSet(generics.DestroyAPIView):
    serializer_class = SpaceDeviceSerializer
    lookup_field = "id"
    queryset = SpaceDevice.objects.all()

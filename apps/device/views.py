import logging

from common.apps.space.models import Space
from common.pagination.base_pagination import BasePagination
from common.utils.switch_tenant import UseTenantFromRequestMixin
from django.db.models import OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.device.contants import DeviceStatus
from apps.device.models import Device, DeviceTransformedData, SpaceDevice, Trip
from apps.device.serializers import (
    CreateSpaceDeviceSerializer,
    DeviceSerializer,
    DeviceTransformedDataSerializer,
    FormatDeviceSerializer,
    GetDeviceSerializer,
    SpaceDeviceSerializer,
    TripDetailSerializer,
    TripListSerializer,
    UpdateSpaceDeviceSerializer,
)
from apps.device.services.trip_analyzer import TripAnalyzerService

logger = logging.getLogger(__name__)


class DeviceViewSet(UseTenantFromRequestMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["created_at"]
    search_fields = ["status"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return GetDeviceSerializer
        return DeviceSerializer

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

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateSpaceDeviceSerializer
        return SpaceDeviceSerializer

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
        include_latest_checkpoint = (
            str(self.request.GET.get("include_latest_checkpoint", "")).lower()
            == "true"
        )
        queryset = SpaceDevice.objects.filter(space=space).select_related("device")
        if include_latest_checkpoint:
            queryset = queryset.select_related("device__lorawan_device")
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "include_latest_checkpoint",
                openapi.IN_QUERY,
                description="Include get_latest_checkpoint in response (true/false)",
                type=openapi.TYPE_BOOLEAN,
                default=False,
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        include_latest_checkpoint = (
            str(request.query_params.get("include_latest_checkpoint", "")).lower()
            == "true"
        )
        serializer_context = self.get_serializer_context()
        serializer_context["include_latest_checkpoint"] = include_latest_checkpoint

        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context=serializer_context
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            queryset, many=True, context=serializer_context
        )
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        space = self._get_space()
        dev_eui = serializer.validated_data.pop("dev_eui")
        device = Device.objects.filter(lorawan_device__dev_eui=dev_eui).first()
        if not device:
            return Response(
                {"detail": f"Device with dev_eui = {dev_eui} not in the organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if device.status == DeviceStatus.ACTIVE:
            return Response(
                {"detail": f"Device with dev_eui = {dev_eui} not in the inventory"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device.status = DeviceStatus.ACTIVE
        device.save()
        serializer.save(space=space, device=device)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FindDeviceByCodeView(views.APIView):
    def get(self, request, *args, **kwargs):
        claim_code = kwargs.get("claim_code")
        device = Device.objects.filter(lorawan_device__claim_code=claim_code).first()
        if not device:
            return Response(
                {"result": "The device not found in the organization!"},
                status.HTTP_404_NOT_FOUND,
            )
        if device.status != DeviceStatus.IN_INVENTORY:
            return Response(
                {"result": "The device has been used elsewhere!"},
                status.HTTP_400_BAD_REQUEST,
            )
        return Response(DeviceSerializer(device).data, status=200)


class DeleteSpaceDeviceViewSet(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = "id"
    queryset = SpaceDevice.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SpaceDeviceSerializer
        return UpdateSpaceDeviceSerializer


class DeviceTransformedDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceTransformedData.objects.all()
    serializer_class = DeviceTransformedDataSerializer


class TripViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    filterset_fields = ["space_device__device_id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return None
        space_slug_name = self.request.headers.get("X-Space", None)
        if space_slug_name is None:
            raise ParseError("X-Space header is required")

        filters = {
            "space_device__space__slug_name": space_slug_name,
            "space_device__space__is_active": True,
        }

        queryset = Trip.objects.filter(**filters).select_related("space_device__space")

        if self._should_include_checkpoints():
            queryset = queryset.select_related(
                "space_device",
                "space_device__device",
                "space_device__device__lorawan_device",
            )

        return queryset

    def get_serializer_class(self):
        return (
            TripDetailSerializer
            if self.action == "retrieve"
            else TripListSerializer
        )

    def _should_include_checkpoints(self):
        return self.action == "retrieve"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        trip_analyzer = TripAnalyzerService()
        trip_with_locations = trip_analyzer.get_trip_with_locations(
            trip=instance,
            organization_slug=instance.space_device.space.slug_name,
        )

        serializer = self.get_serializer(trip_with_locations)
        return Response(serializer.data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "space_device__device_id",
                openapi.IN_QUERY,
                description="Filter trips by Device ID",
                type=openapi.TYPE_STRING,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        # Always analyze the current trip when listing
        device_id = request.query_params.get("space_device__device_id")

        if not device_id:
            raise ParseError("Device ID (space_device__device_id) query parameter is required.")

        trip_analyzer = TripAnalyzerService()
        space_device = SpaceDevice.objects.select_related(
            "device", "space"
        ).get(device__id=device_id)
        current_trip = Trip.objects.filter(
            space_device=space_device,
            is_finished=False
        ).order_by('-started_at').first()

        trip_analyzer.analyze_and_update_current_trip(space_device, current_trip)

        # Get the trips (including any newly created ones)
        queryset = self.filter_queryset(self.get_queryset())
        logger.info(f"Found {queryset.count()} trips in queryset")

        # List never includes checkpoints
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            return response

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)


class DeviceLookupView(UseTenantFromRequestMixin, generics.GenericAPIView):
    serializer_class = FormatDeviceSerializer
    lookup_field = "lorawan_device__dev_eui"
    lookup_url_kwarg = "dev_eui"
    queryset = Device.objects.select_related(
        "device_model", "lorawan_device"
    ).prefetch_related("space_devices")

    def get_queryset(self):
        qs = super().get_queryset()
        space_slug = Subquery(
            SpaceDevice.objects.filter(device_id=OuterRef("pk")).values(
                "space__slug_name"
            )[:1]
        )

        return qs.annotate(space_slug=space_slug)

    def get(self, request, *args, **kwargs):
        try:
            device = self.get_object()
        except Device.DoesNotExist:
            dev_eui = kwargs.get(self.lookup_url_kwarg)
            return Response(
                {"detail": f"Device with DevEUI '{dev_eui}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(device).data, status=status.HTTP_200_OK)

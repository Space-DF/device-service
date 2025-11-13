from common.apps.space.models import Space
from common.pagination.base_pagination import BasePagination
from common.utils.switch_tenant import UseTenantFromRequestMixin
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, views, viewsets
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
            str(self.request.query_params.get("include_latest_checkpoint", "")).lower()
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


class TripViewSet(viewsets.ModelViewSet):
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
            if self.action in ["retrieve", "list"]
            else TripListSerializer
        )

    def _should_include_checkpoints(self):
        include_checkpoints = getattr(self.request, "query_params", {}).get(
            "include_checkpoints"
        )
        return include_checkpoints is not None and include_checkpoints.lower() == "true"

    def _extract_trip_metadata(self, trip):
        return {
            "trip": trip,
            "dev_eui": trip.space_device.device.lorawan_device.dev_eui,
            "start": trip.started_at,
            "end": trip.ended_at or timezone.now(),
        }

    def _get_transformed_data_queryset(self, dev_euis, min_start, max_end):
        return (
            DeviceTransformedData.objects.only(
                "id",
                "timestamp",
                "data",
                "source",
                "metadata",
                "device_reference",
                "device_eui",
            )
            .filter(
                device_eui__in=dev_euis,
                timestamp__gte=min_start,
                timestamp__lte=max_end,
            )
            .order_by("device_eui", "timestamp")
        )

    def _filter_transformed_data_by_time(self, transformed_data, start_time, end_time):
        return [
            data_record
            for data_record in transformed_data
            if start_time <= data_record.timestamp <= end_time
        ]

    def _attach_data_to_trip(self, trip, transformed_data):
        setattr(trip, "checkpoints", transformed_data)

    def _attach_transformed_data(self, trips):
        if not trips:
            return

        is_single_trip = not isinstance(trips, (list, tuple))
        trip_list = [trips] if is_single_trip else trips

        trip_metadata = [self._extract_trip_metadata(trip) for trip in trip_list]

        if not trip_metadata:
            return

        dev_euis = list({meta["dev_eui"] for meta in trip_metadata})
        min_start = min(meta["start"] for meta in trip_metadata)
        max_end = max(meta["end"] for meta in trip_metadata)

        all_transformed_data = list(
            self._get_transformed_data_queryset(dev_euis, min_start, max_end)
        )

        # Group data by device EUI for efficient lookup
        data_by_eui = {}
        for data in all_transformed_data:
            data_by_eui.setdefault(data.device_eui, []).append(data)

        # Filter and attach data to each trip
        for meta in trip_metadata:
            eui_data = data_by_eui.get(meta["dev_eui"], [])
            filtered_data = self._filter_transformed_data_by_time(
                eui_data, meta["start"], meta["end"]
            )
            self._attach_data_to_trip(meta["trip"], filtered_data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "include_checkpoints",
                openapi.IN_QUERY,
                description="Include DeviceCheckpoints in response (true/false)",
                type=openapi.TYPE_BOOLEAN,
                default=False,
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if self._should_include_checkpoints():
            self._attach_transformed_data(instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "include_checkpoints",
                openapi.IN_QUERY,
                description="Include DeviceCheckpoints in response (true/false)",
                type=openapi.TYPE_BOOLEAN,
                default=False,
            ),
            openapi.Parameter(
                "space_device__device_id",
                openapi.IN_QUERY,
                description="Filter trips by Device ID",
                type=openapi.TYPE_STRING,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            if self._should_include_checkpoints():
                self._attach_transformed_data(page)

            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        if self._should_include_checkpoints():
            trips = list(queryset)
            self._attach_transformed_data(trips)
            serializer = self.get_serializer(trips, many=True)
        else:
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

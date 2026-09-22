import logging

from common.apps.billing.mixins import QuotaMixin
from common.apps.space.models import Space
from common.pagination.base_pagination import BasePagination
from common.utils.switch_tenant import UseTenantFromRequestMixin
from common.views.deactivation import DeactivationMixin
from common.views.space import SpaceListCreateAPIView, SpaceUpdateAPIView
from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.device.constants import DeviceStatus
from apps.device.filters import DeviceFilter, SpaceDeviceFilter, TripFilter
from apps.device.models import Device, SpaceDevice, Trip
from apps.device.quotas import DeviceQuota
from apps.device.serializers import (
    CreateSpaceDeviceSerializer,
    DeviceSerializer,
    FormatDeviceSerializer,
    FormatSpaceDeviceSerializer,
    GetDeviceSerializer,
    SpaceDeviceSerializer,
    TripDetailSerializer,
    TripListSerializer,
    UpdateSpaceDevicePositionSerializer,
    UpdateSpaceDeviceSerializer,
)
from apps.device.services.device_profile_resolver import get_device_profile_context
from apps.device.services.device_subscription_service import (
    fill_active_slot_after_delete,
)
from apps.device.services.entity_properties_context import (
    _entity_properties_context,
    _organization_slug,
)
from apps.device.services.space_device_list_service import SpaceDeviceListService
from apps.device.services.trip_analyzer import TripAnalyzerService

logger = logging.getLogger(__name__)


class DeviceViewSet(
    DeactivationMixin,
    UseTenantFromRequestMixin,
    QuotaMixin,
    viewsets.ModelViewSet,
):
    queryset = Device.objects.select_related(
        "lorawan_device",
        "lorawan_device__network_server",
        "api_device",
    ).all()
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter, DjangoFilterBackend]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    search_fields = ["lorawan_device__dev_eui", "api_device__serial_number"]
    filterset_class = DeviceFilter
    quota_classes = [DeviceQuota]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return GetDeviceSerializer
        return DeviceSerializer

    def get_serializer(self, *args, **kwargs):
        if self.action in ["list", "retrieve"] and args:
            items = args[0] if kwargs.get("many", False) else [args[0]]
            context = kwargs.get("context", self.get_serializer_context())
            context = get_device_profile_context(context, items)
            kwargs["context"] = _entity_properties_context(
                context,
                items,
                _organization_slug(self.request),
            )
        return super().get_serializer(*args, **kwargs)

    def perform_destroy(self, instance):
        fill_active_slot = not instance.is_deactivated
        org_slug = _organization_slug(self.request)
        with transaction.atomic():
            super().perform_destroy(instance)
            fill_active_slot_after_delete(fill_active_slot, org_slug)

    @swagger_auto_schema(
        method="post",
        request_body=DeviceSerializer(many=True),
        responses={201: DeviceSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        serializer = self.get_serializer(
            data=request.data,
            many=True,
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=False)
        created_devices = serializer.save()

        failed_data = getattr(serializer, "_failed_data", [])
        total_failed = getattr(serializer, "_total_failed", 0)

        return Response(
            {
                "total_created": len(created_devices),
                "total_failed": total_failed,
                "failed_devices": failed_data,
            },
            status=status.HTTP_201_CREATED,
        )


class SpaceDeviceSerializationMixin:
    entity_properties_context = False

    def get_space_device_serializer_context(self, items, base_context=None):
        context = get_device_profile_context(
            base_context or self.get_serializer_context(),
            items,
        )
        if self.entity_properties_context:
            context = _entity_properties_context(
                context,
                items,
                _organization_slug(self.request),
            )
        return context

    def get_space_device_list_response(self, items):
        page = self.paginate_queryset(items)
        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context=self.get_space_device_serializer_context(page),
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            items,
            many=True,
            context=self.get_space_device_serializer_context(items),
        )
        return Response(serializer.data)

    def get_object(self):
        instance = super().get_object()
        if self.request.method == "GET":
            self._space_device_context_items = [instance]
        return instance

    def get_serializer_context(self):
        context = super().get_serializer_context()
        items = getattr(self, "_space_device_context_items", None)
        if items is None:
            return context
        return self.get_space_device_serializer_context(items, base_context=context)


class ListCreateSpaceDeviceView(
    SpaceDeviceSerializationMixin,
    SpaceListCreateAPIView,
):
    queryset = SpaceDevice.objects.select_related(
        "device",
        "device__lorawan_device",
        "device__lorawan_device__network_server",
        "device__api_device",
        "floor",
        "area",
        "facility",
        "position",
        "building",
    ).all()
    serializer_class = SpaceDeviceSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter, DjangoFilterBackend]
    filterset_class = SpaceDeviceFilter
    ordering_fields = ["created_at", "name"]
    space_field = "space"
    entity_properties_context = True
    search_fields = [
        "name",
        "description",
        "device__lorawan_device__dev_eui",
        "device__api_device__serial_number",
        "device__device_model",
    ]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateSpaceDeviceSerializer
        return SpaceDeviceSerializer

    def list(self, request, *args, **kwargs):
        service = SpaceDeviceListService(request)
        queryset = self.filter_queryset(self.get_queryset())
        results = service.get_combined_results(queryset)
        return self.get_space_device_list_response(results)


class FindDeviceByCodeView(DeactivationMixin, views.APIView):
    def get(self, request, *args, **kwargs):
        claim_code = kwargs.get("claim_code")
        device = Device.objects.filter(claim_code=claim_code).first()
        if not device:
            return Response(
                {"result": "The device not found in the organization!"},
                status.HTTP_404_NOT_FOUND,
            )
        self.check_deactivated(device)
        if device.status != DeviceStatus.IN_INVENTORY:
            return Response(
                {"result": "The device has been used elsewhere!"},
                status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            DeviceSerializer(
                device,
                context=_entity_properties_context(
                    get_device_profile_context({}, [device]),
                    [device],
                    _organization_slug(request),
                ),
            ).data,
            status=200,
        )


class DeleteSpaceDeviceViewSet(
    SpaceDeviceSerializationMixin,
    DeactivationMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    lookup_field = "id"
    queryset = SpaceDevice.objects.select_related("device", "space").all()
    deactivation = ["device", "space"]
    entity_properties_context = True

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SpaceDeviceSerializer
        return UpdateSpaceDeviceSerializer


class ListTripView(DeactivationMixin, generics.ListAPIView):
    deactivation = ["device"]
    permission_classes = [AllowAny]
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    filterset_class = TripFilter
    ordering = ["-last_report"]
    queryset = (
        Trip.objects.filter(
            Q(device__deactivated_at__isnull=True)
            | Q(started_at__lt=F("device__deactivated_at"))
        )
        .select_related(
            "device",
            "device__lorawan_device",
            "device__api_device",
        )
        .prefetch_related("device__space_devices")
    )
    serializer_class = TripListSerializer

    def get_queryset(self):
        space_slug_name = self.request.headers.get("X-Space", None)
        if space_slug_name is None:
            raise ParseError("X-Space header is required")

        space = Space.objects.filter(slug_name=space_slug_name).first()
        self.check_deactivated(space)

        return self.queryset.filter(
            Q(
                device__space_devices__space__slug_name=space_slug_name,
                device__space_devices__space__is_active=True,
            )
            | Q(device__is_published=True, device__space_devices__isnull=True)
        ).distinct()

    def list(self, request, *args, **kwargs):
        device_id = request.query_params.get("device_id")
        if not device_id:
            return super().list(request, *args, **kwargs)

        trip_analyzer = TripAnalyzerService()
        trip_analyzer.analyze_and_update_current_trip(
            request.tenant.slug_name, device_id
        )
        return super().list(request, *args, **kwargs)


class RetrieveTripView(DeactivationMixin, generics.RetrieveAPIView):
    deactivation = ["device"]
    deactivation_allowed_methods = ["GET"]
    permission_classes = [AllowAny]
    lookup_field = "id"
    queryset = (
        Trip.objects.filter(
            Q(device__deactivated_at__isnull=True)
            | Q(started_at__lt=F("device__deactivated_at"))
        )
        .select_related(
            "device",
            "device__lorawan_device",
            "device__api_device",
        )
        .prefetch_related("device__space_devices")
    )
    serializer_class = TripDetailSerializer

    def get_queryset(self):
        space_slug_name = self.request.headers.get("X-Space", None)
        if space_slug_name is None:
            raise ParseError("X-Space header is required")

        space = Space.objects.filter(slug_name=space_slug_name).first()
        self.check_deactivated(space)

        return self.queryset.filter(
            Q(
                device__space_devices__space__slug_name=space_slug_name,
                device__space_devices__space__is_active=True,
            )
            | Q(device__is_published=True, device__space_devices__isnull=True)
        ).distinct()

    def get_object(self):
        instance = super().get_object()
        trip_analyzer = TripAnalyzerService()
        return trip_analyzer.get_trip_with_locations(
            instance, self.request.tenant.slug_name
        )


class DeviceLookupView(UseTenantFromRequestMixin, generics.RetrieveAPIView):
    swagger_schema = None
    serializer_class = FormatDeviceSerializer
    queryset = Device.objects.select_related(
        "lorawan_device",
        "api_device",
    ).prefetch_related("space_devices")

    def get_queryset(self):
        qs = super().get_queryset()
        space_slug = Subquery(
            SpaceDevice.objects.filter(device_id=OuterRef("pk")).values(
                "space__slug_name"
            )[:1]
        )

        return qs.annotate(
            device_id=Coalesce("lorawan_device__id", "api_device__id"),
            space_slug=space_slug,
        )

    def get_object(self):
        device_identifier = self.kwargs.get("identifier", "").strip()
        lorawan_dev_eui = device_identifier.lower()
        return get_object_or_404(
            self.get_queryset(),
            Q(lorawan_device__dev_eui=lorawan_dev_eui)
            | Q(api_device__serial_number=device_identifier),
        )


class SpaceDeviceLookupView(UseTenantFromRequestMixin, generics.RetrieveAPIView):
    swagger_schema = None
    serializer_class = FormatSpaceDeviceSerializer
    queryset = SpaceDevice.objects.all()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        device_id = self.kwargs["device_id"]

        return get_object_or_404(queryset, device_id=device_id)


class RetrieveSpaceDeviceView(
    SpaceDeviceSerializationMixin,
    DeactivationMixin,
    generics.RetrieveAPIView,
):
    serializer_class = SpaceDeviceSerializer
    lookup_field = "device_id"
    deactivation = ["device", "space"]
    entity_properties_context = True
    queryset = SpaceDevice.objects.select_related(
        "device",
        "device__lorawan_device",
        "device__lorawan_device__network_server",
        "device__api_device",
        "floor",
        "area",
        "facility",
        "position",
        "space",
    ).all()


class ListPublicSpaceDeviceView(
    SpaceDeviceSerializationMixin,
    generics.ListAPIView,
):
    serializer_class = SpaceDeviceSerializer
    entity_properties_context = True
    pagination_class = BasePagination
    permission_classes = [AllowAny]
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    search_fields = [
        "lorawan_device__dev_eui",
        "api_device__serial_number",
        "device_model",
    ]

    def get_queryset(self):
        service = SpaceDeviceListService(self.request)
        return (
            service.get_public_devices_queryset()
            .filter(is_deactivated=False)
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return self.get_space_device_list_response(queryset)


class RetrievePublicSpaceDeviceView(
    SpaceDeviceSerializationMixin,
    DeactivationMixin,
    generics.RetrieveAPIView,
):
    serializer_class = SpaceDeviceSerializer
    entity_properties_context = True
    permission_classes = [AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        return Device.objects.select_related("lorawan_device", "api_device").filter(
            is_published=True,
            space_devices__isnull=True,
        )


class BulkUpdateSpaceDeviceView(SpaceUpdateAPIView):
    queryset = SpaceDevice.objects.select_related("device", "space", "position").all()
    serializer_class = UpdateSpaceDevicePositionSerializer
    space_field = "space"
    deactivation = ["device", "space"]
    http_method_names = ["put"]

    @swagger_auto_schema(
        request_body=UpdateSpaceDevicePositionSerializer(many=True),
        responses={200: UpdateSpaceDevicePositionSerializer(many=True)},
    )
    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(many=True, data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = [item["id"] for item in serializer.validated_data]
        instances = self.filter_queryset(self.get_queryset()).in_bulk(
            ids,
            field_name="id",
        )

        missing_ids = set(ids) - set(instances.keys())
        if missing_ids:
            raise ParseError(
                f"Not found for id(s): " f"{', '.join(map(str, missing_ids))}"
            )

        ordered_instances = [
            instances[item["id"]] for item in serializer.validated_data
        ]
        for instance in ordered_instances:
            self.check_deactivated_object(instance)

        with transaction.atomic():
            serializer = self.get_serializer(
                ordered_instances, data=request.data, many=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

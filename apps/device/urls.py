from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.device.views import (
    BulkUpdateSpaceDeviceView,
    DeleteSpaceDeviceViewSet,
    DeviceLookupView,
    DeviceViewSet,
    FindDeviceByCodeView,
    ListCreateSpaceDeviceViewSet,
    ListPublicSpaceDeviceView,
    RetrievePublicSpaceDeviceView,
    RetrieveSpaceDeviceView,
    SpaceDeviceLookupView,
    TripViewSet,
)

app_name = "device"

router = DefaultRouter()
router.register("devices", DeviceViewSet)
router.register("trips", TripViewSet, basename="trip")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "public/device-spaces",
        ListPublicSpaceDeviceView.as_view(),
        name="public_device_spaces",
    ),
    path(
        "public/device-spaces/<uuid:id>",
        RetrievePublicSpaceDeviceView.as_view(),
        name="public_device_spaces_detail",
    ),
    path(
        "device-spaces/<uuid:device_id>/internal",
        SpaceDeviceLookupView.as_view(),
        name="device_spaces_lookup",
    ),
    path(
        "device-spaces/device/<uuid:device_id>",
        RetrieveSpaceDeviceView.as_view(),
        name="device_spaces_by_device_id",
    ),
    path("device-spaces", ListCreateSpaceDeviceViewSet.as_view(), name="device_spaces"),
    path(
        "device-spaces/bulk-update",
        BulkUpdateSpaceDeviceView.as_view(),
        name="bulk_update_device_spaces",
    ),
    path(
        "device-spaces/<str:id>",
        DeleteSpaceDeviceViewSet.as_view(),
        name="delete_update_device_spaces",
    ),
    path(
        "devices/<str:claim_code>/check",
        FindDeviceByCodeView.as_view(),
        name="check_device",
    ),
    path(
        "devices/<str:dev_eui>/internal",
        DeviceLookupView.as_view(),
        name="device_lookup",
    ),
]

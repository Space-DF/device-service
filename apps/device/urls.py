from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.device.views import (
    DeleteSpaceDeviceViewSet,
    DeviceLookupView,
    DeviceViewSet,
    FindDeviceByCodeView,
    ListCreateSpaceDeviceViewSet,
    TripViewSet,
)

app_name = "device"

router = DefaultRouter()
router.register("devices", DeviceViewSet)
router.register("trips", TripViewSet, basename="trip")

urlpatterns = [
    path("", include(router.urls)),
    path("device-spaces", ListCreateSpaceDeviceViewSet.as_view(), name="device_spaces"),
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

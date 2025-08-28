from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.device.views import (
    DeleteSpaceDeviceViewSet,
    DeviceViewSet,
    ListCreateSpaceDeviceViewSet,
)

app_name = "device"

router = DefaultRouter()
router.register("devices", DeviceViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("device-spaces", ListCreateSpaceDeviceViewSet.as_view(), name="device_spaces"),
    path(
        "device-spaces/<str:id>",
        DeleteSpaceDeviceViewSet.as_view(),
        name="delete_device_spaces",
    ),
]

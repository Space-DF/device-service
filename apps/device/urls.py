from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.device.views import (
    DeviceTransformedDataViewSet,
    DeviceViewSet,
    SpaceDeviceViewSet,
)

app_name = "device"

router = DefaultRouter()
router.register("devices", DeviceViewSet)
router.register("device-spaces", SpaceDeviceViewSet)
router.register("device-transformed-data", DeviceTransformedDataViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

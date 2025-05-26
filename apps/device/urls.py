from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.device.views import DeviceViewSet, SpaceDeviceViewSet

app_name = "device"

router = DefaultRouter()
router.register("devices", DeviceViewSet)
router.register("device-spaces", SpaceDeviceViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from device_model.views import DeviceManufactureViewSet, DeviceModelViewSet

app_name = "device_model"

router = DefaultRouter()
router.register("manufacturers", DeviceManufactureViewSet)
router.register("models", DeviceModelViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

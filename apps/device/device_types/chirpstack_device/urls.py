from rest_framework.routers import DefaultRouter

from apps.device.device_types.chirpstack_device.views import ChirpstackDeviceViewSet

router = DefaultRouter()
router.register("chirpstack-device", ChirpstackDeviceViewSet)

urlpatterns = router.urls

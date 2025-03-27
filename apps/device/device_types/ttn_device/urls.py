from rest_framework.routers import DefaultRouter
from apps.device.device_types.ttn_device.views import TtnDeviceViewSet

router = DefaultRouter()
router.register("ttn-device", TtnDeviceViewSet)

urlpatterns = router.urls
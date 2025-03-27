from rest_framework.routers import DefaultRouter
from apps.device.device_types.mqtt_device.views import MqttDeviceViewSet

router = DefaultRouter()
router.register("mqtt-device", MqttDeviceViewSet)

urlpatterns = router.urls
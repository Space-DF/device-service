from rest_framework.routers import DefaultRouter
from apps.device.device_types.ttn_gateway.views import TtnGatewayViewSet

router = DefaultRouter()
router.register("ttn-gateway", TtnGatewayViewSet)

urlpatterns = router.urls
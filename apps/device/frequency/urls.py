from rest_framework.routers import DefaultRouter

from apps.device.frequency.views import LoraFrequencyViewSet

router = DefaultRouter()
router.register("frequency", LoraFrequencyViewSet)

urlpatterns = router.urls

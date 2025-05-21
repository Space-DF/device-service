from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.device_connector.views import APIApplicationView

app_name = "device_connector"

router = DefaultRouter()
router.register("device-connector", APIApplicationView)

urlpatterns = [
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.network_server.views import NetworkServerViewSet

app_name = "network_server"

router = DefaultRouter()
router.register("network-server", NetworkServerViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

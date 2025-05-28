from django.urls import path

from apps.network_server.views import NetworkServerView

app_name = "network_server"

urlpatterns = [
    path("network-server/", NetworkServerView.as_view(), name="network_server"),
]

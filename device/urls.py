from django.urls import path

from .views import DeviceListCreateAPIView, DeviceRetrieveUpdateDestroyAPIView

app_name = "device"

urlpatterns = [
    path("devices/", DeviceListCreateAPIView.as_view(), name="device-list-create"),
    path(
        "devices/<uuid:pk>/",
        DeviceRetrieveUpdateDestroyAPIView.as_view(),
        name="device-detail",
    ),
]

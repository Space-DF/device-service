from django.urls import path

from .views import DeviceListCreateAPIView

app_name = "device"

urlpatterns = [
    path("devices/", DeviceListCreateAPIView.as_view(), name="device-list-create"),
]

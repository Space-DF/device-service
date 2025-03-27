from django.urls import include, path

app_name = "device"

urlpatterns = [
    path("", include("apps.device.frequency.urls")),
    path("", include("apps.device.device_types.chirpstack_device.urls")),
    path("", include("apps.device.device_types.mqtt_device.urls")),
    path("", include("apps.device.device_types.ttn_device.urls")),
    path("", include("apps.device.device_types.ttn_gateway.urls")),
]

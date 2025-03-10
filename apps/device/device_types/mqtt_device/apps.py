from django.apps import AppConfig


class MqttDeviceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.device.device_types.mqtt_device"

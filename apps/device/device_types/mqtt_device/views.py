from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets
from apps.device.device_types.mqtt_device.serializers import MqttDeviceSerializer
from apps.device.device_types.mqtt_device.models import MqttDevice


class MqttDeviceViewSet(viewsets.ModelViewSet):
    queryset = MqttDevice.objects.all()
    pagination_class = BasePagination
    serializer_class = MqttDeviceSerializer
    
from common.admin.base_admin import ListDisplayMixin
from django.contrib import admin

from .models import MqttDevice


@admin.register(MqttDevice)
class ChirpstackDeviceAdmin(ListDisplayMixin):
    pass

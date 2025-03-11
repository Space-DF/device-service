from common.admin.base_admin import ListDisplayMixin
from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(ListDisplayMixin):
    pass

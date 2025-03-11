from common.admin.base_admin import ListDisplayMixin
from django.contrib import admin

from .models import ChirpstackDevice


@admin.register(ChirpstackDevice)
class ChirpstackDeviceAdmin(ListDisplayMixin):
    pass

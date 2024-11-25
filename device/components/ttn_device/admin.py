from common.admin.base_admin import ListDisplayMixin
from django.contrib import admin

from .models import TtnDevice


@admin.register(TtnDevice)
class TtnDeviceAdmin(ListDisplayMixin):
    pass

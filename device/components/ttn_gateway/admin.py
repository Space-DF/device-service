from common.admin.base_admin import ListDisplayMixin
from django.contrib import admin

from .models import TtnGateway


@admin.register(TtnGateway)
class TtnGatewayAdmin(ListDisplayMixin):
    pass

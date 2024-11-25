from common.admin.base_admin import ListDisplayMixin
from django.contrib import admin

from .models import LoraFrequency


@admin.register(LoraFrequency)
class LoraFrequencyAdmin(ListDisplayMixin):
    pass

from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.device.frequency.models import LoraFrequency
from apps.device.frequency.serializers import LoraFrequencySerializer


class LoraFrequencyViewSet(viewsets.ModelViewSet):
    queryset = LoraFrequency.objects.all()
    serializer_class = LoraFrequencySerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["phy_version"]
    search_fields = ["dev_eui"]
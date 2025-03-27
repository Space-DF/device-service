from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets
from apps.device.device_types.ttn_gateway.serializers import TtnGatewaySerializer
from apps.device.device_types.ttn_gateway.models import TtnGateway


class TtnGatewayViewSet(viewsets.ModelViewSet):
    queryset = TtnGateway.objects.all()
    pagination_class = BasePagination
    serializer_class = TtnGatewaySerializer
    
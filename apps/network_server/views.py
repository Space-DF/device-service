from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.network_server.models import NetworkServer
from apps.network_server.serializers import NetworkServerSerializer


class NetworkServerViewSet(viewsets.ModelViewSet):
    queryset = NetworkServer.objects.all()
    serializer_class = NetworkServerSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name"]

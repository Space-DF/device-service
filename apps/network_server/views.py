from common.pagination.base_pagination import BasePagination
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.network_server.services import get_network_servers


class NetworkServerView(APIView):
    pagination_class = BasePagination()

    def get(self, request: Request):
        search = request.query_params.get("search")
        all_servers = get_network_servers(name=search)

        paginator = self.pagination_class
        paginated_data = paginator.paginate_queryset(all_servers, request)
        return paginator.get_paginated_response(paginated_data)

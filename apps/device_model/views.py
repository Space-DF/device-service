from common.pagination.base_pagination import BasePagination
from django.db import connection
from django_tenants.utils import get_tenant_domain_model
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.device_model.models import DeviceManufacture, DeviceModel
from apps.device_model.serializers import (
    DeviceManufactureSerializer,
    DeviceModelSerializer,
)


class UseTenantFromRequestMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        org = request.headers.get("X-Organization", None)
        if not org:
            raise ParseError("Missing 'organization' parameter")

        domain_model = get_tenant_domain_model()
        try:
            domain = domain_model.objects.select_related("tenant").get(
                tenant__schema_name=org
            )
            tenant = domain.tenant
        except domain_model.DoesNotExist:
            raise NotFound(f"Tenant '{org}' not found")

        connection.set_tenant(tenant)
        request.tenant = tenant


class DeviceManufactureViewSet(UseTenantFromRequestMixin, viewsets.ModelViewSet):
    queryset = DeviceManufacture.objects.all()
    serializer_class = DeviceManufactureSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name"]


class DeviceModelViewSet(UseTenantFromRequestMixin, viewsets.ModelViewSet):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer
    pagination_class = BasePagination
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name", "alias"]

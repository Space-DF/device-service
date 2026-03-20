from common.apps.organization.handler import NewOrganizationHandlerBase
from django.db import transaction
from django_tenants.utils import schema_context

from apps.network_server.services import create_network_servers


class NewOrganizationHandler(NewOrganizationHandlerBase):
    @transaction.atomic
    def handle(self):
        with schema_context(self._organization.slug_name):
            create_network_servers()

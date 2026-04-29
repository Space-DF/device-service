from common.apps.organization.handler import NewOrganizationHandlerBase
from common.apps.space.models import Space
from django.db import transaction
from django_tenants.utils import schema_context

from apps.network_server.services import create_network_servers


class NewOrganizationHandler(NewOrganizationHandlerBase):
    @transaction.atomic
    def handle(self):
        with schema_context(self._organization.slug_name):
            create_network_servers()
            Space.objects.get_or_create(
                is_default=True,
                defaults={
                    "name": "Default",
                    "slug_name": f"default-{self._organization.id}",
                    "created_by": self._owner.get("id"),
                },
            )

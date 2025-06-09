from common.apps.organization.handler import NewOrganizationHandlerBase
from django.db import transaction
from django_tenants.utils import schema_context

from apps.device.services import create_action_http
from apps.rule.action.models import Action


class NewOrganizationHandler(NewOrganizationHandlerBase):
    @transaction.atomic
    def handle(self):
        with schema_context(self._organization.slug_name):
            result_create_action = create_action_http(self._organization.slug_name)
            if not result_create_action:
                raise Exception("Failed to create action")

            Action.objects.create(
                enable=result_create_action.get("enable"),
                name=result_create_action.get("name"),
                type=result_create_action.get("type"),
                parameters=result_create_action.get("parameters"),
                resource_opts=result_create_action.get("resource_opts"),
            )

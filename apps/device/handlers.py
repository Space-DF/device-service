from common.apps.organization.handler import (
    DeleteOrganizationHandlerBase,
    NewOrganizationHandlerBase,
)
from django.db import transaction
from django_tenants.utils import schema_context

from apps.device.services import create_action_http
from apps.device_connector.services import delete_action_http, delete_all_by_rule
from apps.rule.action.models import Action
from apps.rule.definition.models import Definition


class NewOrganizationHandler(NewOrganizationHandlerBase):
    @transaction.atomic
    def handle(self, tenant_slug=None):
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


class DeleteOrganizationHandler(DeleteOrganizationHandlerBase):
    def handle(self, tenant_slug=None):
        with schema_context(self._organization.slug_name):
            definitions = Definition.objects.all()
            if definitions:
                for definition in definitions:
                    delete_all_by_rule(definition.rule_id)
            else:
                delete_action_http(f"action_{self._organization.slug_name}_default")

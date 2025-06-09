from common.celery.tasks import task
from django.db import transaction
from django.db.utils import ProgrammingError
from django_tenants.utils import schema_context

from apps.device.services import create_action_http
from apps.rule.action.models import Action


@task(
    name="spacedf.tasks.new_action_output",
    autoretry_for=(ProgrammingError,),
)
@transaction.atomic
def create_new_action_output(slug_name):
    try:
        with schema_context(slug_name):
            action = Action.objects.filter(name=f"action_{slug_name}_default").first()
            if action is None:
                result_create_action = create_action_http(slug_name)
                if not result_create_action:
                    raise Exception("Failed to create action")

                Action.objects.create(
                    enable=result_create_action.get("enable"),
                    name=result_create_action.get("name"),
                    type=result_create_action.get("type"),
                    parameters=result_create_action.get("parameters"),
                    resource_opts=result_create_action.get("resource_opts"),
                )
    except Exception as e:
        raise Exception(f"error: {e}")

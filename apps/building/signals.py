from common.apps.organization.constants import OrganizationTemplate
from common.apps.space.models import Space
from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.building.models import Building


@receiver(post_save, sender=Space)
def create_default_building_for_space(sender, instance, created, **kwargs):
    if not created:
        return

    tenant = connection.get_tenant()
    if getattr(tenant, "template", "") != OrganizationTemplate.SMART_BUILDING:
        return

    Building.objects.get_or_create(
        name="Default Building",
        space_id=instance.id,
        defaults={
            "description": "This is the default building.",
        },
    )

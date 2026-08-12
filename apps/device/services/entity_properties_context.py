from apps.device.services.entity_properties_service import EntityPropertiesService


def _device_ids(items):
    device_ids = set()
    for item in items:
        device = getattr(item, "device", item)
        device_id = getattr(device, "id", None)
        if device_id:
            device_ids.add(str(device_id))
    return device_ids


def _entity_properties_context(context, items, organization_slug):
    return {
        **context,
        "entity_properties_by_device_id": EntityPropertiesService().get_entity_properties_batch(
            _device_ids(items),
            organization_slug,
        ),
    }


def _organization_slug(request):
    tenant = getattr(request, "tenant", None)
    return getattr(tenant, "slug_name", "") or ""

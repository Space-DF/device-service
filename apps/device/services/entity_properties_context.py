from apps.device.models import Device
from apps.device.services.entity_properties_service import EntityPropertiesService


def _device_ids(items):
    device_ids = set()
    for item in items:
        device = getattr(item, "device", item)
        device_id = getattr(device, "id", None)
        if device_id:
            device_ids.add(str(device_id))
    return device_ids


def _device_property_end_dates(items):
    end_dates = {}
    for item in items:
        device = getattr(item, "device", item)
        device_id = getattr(device, "id", None)
        if not device_id or not getattr(device, "is_deactivated", False):
            continue

        end_date = getattr(device, "deactivated_at", None)
        if end_date:
            end_dates[str(device_id)] = end_date.isoformat()
    return end_dates


def _entity_properties_context(context, items, organization_slug):
    return {
        **context,
        "entity_properties_by_device_id": EntityPropertiesService().get_entity_properties_batch(
            _device_ids(items),
            organization_slug,
            _device_property_end_dates(items),
        ),
    }


def _organization_slug(request):
    tenant = getattr(request, "tenant", None)
    return getattr(tenant, "slug_name", "") or ""


def _resolve_entity_properties_from_context(context, obj, org_slug):
    device_id = str(obj.id) if isinstance(obj, Device) else str(obj.device_id)
    properties_by_device_id = context.get("entity_properties_by_device_id", {})
    return properties_by_device_id.get(
        device_id,
        {"device_properties": None, "entities": []},
    )

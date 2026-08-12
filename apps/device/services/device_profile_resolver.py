from functools import lru_cache
from uuid import UUID

from common.utils.tranformer_client import TranformerServiceClient


def get_device_profile_context(context, items):
    return {
        **context,
        "device_profiles_by_model_id": (
            TranformerServiceClient().get_device_profiles_by_model_ids(
                get_device_model_ids(items)
            )
        ),
    }


def get_device_model_ids(items):
    device_model_ids = set()
    for item in items:
        device = getattr(item, "device", item)
        device_model = getattr(device, "device_model", None)
        if device_model:
            device_model_ids.add(str(device_model))
    return device_model_ids


def profile_matches_key_feature(profile, value):
    return str(profile.get("key_feature") or "").strip() == str(value or "").strip()


@lru_cache(maxsize=256)
def find_device_model_ids_by_key_feature(value, device_model_ids):
    matched_ids = []
    profiles = TranformerServiceClient().get_device_profiles_by_model_ids(
        device_model_ids
    )
    for device_model_id, profile in profiles.items():
        if profile_matches_key_feature(profile, value):
            matched_ids.append(device_model_id)
    return tuple(matched_ids)


def resolve_key_feature_filter(value):
    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    try:
        UUID(raw_value)
        return [raw_value]
    except ValueError:
        pass

    from apps.device.models import Device

    device_model_ids = tuple(
        str(device_model)
        for device_model in Device.objects.exclude(device_model__isnull=True)
        .values_list("device_model", flat=True)
        .distinct()
    )
    return list(find_device_model_ids_by_key_feature(raw_value, device_model_ids))

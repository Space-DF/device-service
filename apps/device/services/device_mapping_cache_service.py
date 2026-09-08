import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def clear_device_identifier_cache(slug_name, identifier_type, identifier):
    """
    Clear cached transformer device mapping for a supported device identifier.
    """
    if not slug_name or not identifier_type or not identifier:
        logger.debug(
            "Skipped cache clear: slug_name=%s, identifier_type=%s, identifier=%s",
            slug_name,
            identifier_type,
            identifier,
        )
        return

    cache_key = f"{slug_name}:{identifier_type}:{identifier}"
    logger.info("Clearing device cache: %s", cache_key)
    cache.delete(cache_key)


def clear_device_mapping_cache(slug_name, device):
    if not device:
        return

    identifiers = {
        "lorawan": getattr(getattr(device, "lorawan_device", None), "dev_eui", None),
        "api": getattr(getattr(device, "api_device", None), "serial_number", None),
    }
    for identifier_type, identifier in identifiers.items():
        clear_device_identifier_cache(slug_name, identifier_type, identifier)

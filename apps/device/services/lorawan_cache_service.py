import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def clear_lorawan_cache(slug_name, dev_eui):
    """
    Clear lorawan device cache.
    """
    if slug_name and dev_eui:
        cache_key = f"{slug_name}:lorawan:{dev_eui}"
        logger.info(f"Clearing lorawan cache: {cache_key}")
        cache.delete(cache_key)
    else:
        logger.debug(f"Skipped cache clear: slug_name={slug_name}, dev_eui={dev_eui}")

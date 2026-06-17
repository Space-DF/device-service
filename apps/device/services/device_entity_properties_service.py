import logging
from typing import Any

from common.utils.telemetry_client import TelemetryServiceClient

logger = logging.getLogger(__name__)


class DeviceEntityPropertiesService:
    def __init__(self, telemetry_client: TelemetryServiceClient | None = None):
        self.telemetry_client = telemetry_client or TelemetryServiceClient()

    def get_device_entity_properties(
        self,
        device_id: str,
        organization_slug: str,
    ) -> dict:
        try:
            entities = self.telemetry_client.get_device_entity_properties(
                device_id,
                organization_slug,
            )
            return {
                "entities": entities or [],
                "device_properties": self._build_device_properties(entities or []),
            }
        except Exception:
            logger.exception(
                "Error fetching device entity properties for device %s",
                device_id,
            )
            return {"device_properties": None, "entities": []}

    def _build_device_properties(self, entities: list[dict]) -> dict | None:
        device_properties: dict[str, Any] = {}

        for entity in entities:
            category = entity.get("category")
            value = entity.get("value")

            if not category or value is None:
                continue

            if category == "location" and isinstance(value, dict):
                latest_checkpoint = {
                    "timestamp": entity.get("time_end"),
                    "latitude": value.get("latitude"),
                    "longitude": value.get("longitude"),
                    "bearing": value.get("bearing"),
                }
                if (
                    latest_checkpoint["latitude"] is not None
                    and latest_checkpoint["longitude"] is not None
                ):
                    device_properties["latest_checkpoint"] = latest_checkpoint
                continue

            device_properties[category] = value

        return device_properties or None

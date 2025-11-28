"""
Telemetry Service Client for fetching location history data
"""
import logging
from dataclasses import dataclass
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


def _parse_timestamp(timestamp: str) -> datetime:
    """
    Parse timestamp from various formats

    Args:
        timestamp: Timestamp in various formats

    Returns:
        datetime object
    """
    if isinstance(timestamp, datetime):
        return timestamp

    if isinstance(timestamp, str):
        # Try ISO format first
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt)
            return dt
        except ValueError:
            pass

        # Try other common formats
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp, fmt)
                return timezone.make_aware(dt)
            except ValueError:
                continue

    raise ValueError(f"Unable to parse timestamp: {timestamp}")


@dataclass
class LocationPoint:
    """Data class for a single location point"""

    timestamp: datetime
    latitude: float
    longitude: float
    accuracy: float
    device_id: str


class TelemetryServiceClient:
    """Client for interacting with the Telemetry Service API"""

    def __init__(self, base_url: str | None = None):
        """
        Initialize the telemetry service client

        Args:
            base_url: Base URL for the telemetry service. If not provided, uses settings
        """
        self.base_url = base_url or getattr(
            settings, "TELEMETRY_SERVICE_URL", "http://telemetry:8080"
        )
        self.timeout = 30  # seconds

    def get_location_history(
        self,
        device_id: str,
        space_slug: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 10000,
    ) -> list[LocationPoint]:
        """
        Fetch location history for a device from the telemetry service

        Args:
            device_id: The device ID to fetch data for
            space_slug: The organization slug
            start: Start timestamp (optional)
            end: End timestamp (optional)
            limit: Maximum number of records to fetch

        Returns:
            List of location data points sorted by timestamp

        Raises:
            RequestException: If the API call fails
        """
        endpoint = f"{self.base_url}/telemetry/v1/location/history"

        params = {"device_id": device_id, "space_slug": space_slug, "limit": limit}

        if start:
            params["start"] = (
                start.isoformat() if isinstance(start, datetime) else start
            )

        if end:
            params["end"] = end.isoformat() if isinstance(end, datetime) else end

        try:
            logger.info("Device ID: %s", device_id)
            logger.info(f"Start: {start}")
            logger.info(f"End: {end}")
            logger.info(f"Limit: {limit}")
            logger.info(f"Endpoint: {endpoint}")
            logger.info(f"Request params: {params}")

            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            logger.info(f"Response status code: {response.status_code}")

            if response.status_code == 404:
                logger.warning(f"404 - No location data found for device {device_id}")
                return []

            response.raise_for_status()

            data = response.json()
            locations = data.get("locations", [])
            logger.info(f"Received {len(locations)} locations")

            formatted_locations: list[LocationPoint] = []
            for loc in locations:
                formatted_locations.append(
                    LocationPoint(
                        timestamp=_parse_timestamp(loc.get("timestamp", "")),
                        latitude=loc.get("latitude", 0),
                        longitude=loc.get("longitude", 0),
                        accuracy=loc.get("accuracy", 0),
                        device_id=device_id,
                    )
                )

            return formatted_locations
        except Timeout:
            logger.error(
                f"Timeout while fetching location history for device {device_id}"
            )
            raise

        except RequestException as e:
            logger.error(
                f"Error fetching location history for device {device_id}: {str(e)}"
            )
            raise

    def get_last_location(
        self, device_id: str, space_slug: str
    ) -> LocationPoint | None:
        """
        Fetch the most recent location for a device from the telemetry service

        Args:
            device_id: The device ID to fetch data for
            space_slug: The organization slug

        Returns:
            The most recent location point, or None if not found
        """
        endpoint = f"{self.base_url}/telemetry/v1/location/last"

        params = {
            "device_id": device_id,
            "space_slug": space_slug,
        }

        try:
            logger.info("Device ID: %s, Organization: %s", device_id, space_slug)

            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            logger.info(f"Response status code: {response.status_code}")

            if response.status_code == 404:
                logger.warning(f"No location data found for device {device_id}")
                return None

            response.raise_for_status()

            data = response.json()
            logger.info(f"Response: {data}")

            # Check for error response
            if "error" in data:
                logger.warning(f"Error from telemetry service: {data['error']}")
                return None

            location_point = LocationPoint(
                timestamp=_parse_timestamp(data.get("timestamp", "")),
                latitude=data.get("latitude", 0),
                longitude=data.get("longitude", 0),
                accuracy=data.get("accuracy", 0),
                device_id=device_id,
            )

            return location_point

        except Timeout:
            logger.error(f"Timeout while fetching last location for device {device_id}")
            return None

        except RequestException as e:
            logger.error(
                f"Error fetching last location for device {device_id}: {str(e)}"
            )
            return None

    def check_health(self) -> bool:
        """
        Check if the telemetry service is healthy and reachable

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/health"
            response = requests.get(endpoint, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telemetry service health check failed: {str(e)}")
            return False

"""
Telemetry Service Client for fetching location history data
"""
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone
from requests.exceptions import RequestException, Timeout

from apps.device.constants import DEFAULT_DISTANCE_THRESHOLD, LocationPoint
from apps.device.services.kalman_filter import KalmanFilterProcessor
from apps.utils.haversine_distance import haversine_distance

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

    def _deduplicate_locations(
        self,
        locations: list[LocationPoint],
        distance_threshold_meters: float = DEFAULT_DISTANCE_THRESHOLD,
    ) -> list[LocationPoint]:
        """
        Remove duplicate/nearby locations within distance threshold.

        Args:
            locations: List of location points sorted by timestamp
            distance_threshold_meters: Distance threshold in meters (default: 50m)

        Returns:
            Deduplicated list of locations
        """
        if not locations or len(locations) == 1:
            return locations

        deduplicated = [locations[0]]

        for current in locations[1:]:
            last = deduplicated[-1]
            distance = haversine_distance(
                last.latitude, last.longitude, current.latitude, current.longitude
            )

            if distance > distance_threshold_meters:
                deduplicated.append(current)

        removed_count = len(locations) - len(deduplicated)
        if removed_count > 0:
            logger.debug(
                f"Deduplication removed {removed_count} duplicate locations "
                f"(threshold: {distance_threshold_meters}m)"
            )

        return deduplicated

    def get_location_history(
        self,
        device_id: str,
        organization_slug: str,
        space_slug: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 10000,
        deduplicate: bool = True,
        distance_threshold_meters: float = DEFAULT_DISTANCE_THRESHOLD,
        use_trajectory_processing: bool = True,
    ) -> list[LocationPoint]:
        """
        Fetch location history for a device from the telemetry service

        Applies trajectory processing:
        1. Remove duplicate/nearby points (GPS noise)
        2. Remove outliers (impossible speeds)
        3. Smooth coordinates (Kalman filter)
        4. Compress trajectory (remove collinear points)

        Args:
            device_id: The device ID to fetch data for
            space_slug: The space slug
            start: Start timestamp (optional)
            end: End timestamp (optional)
            limit: Maximum number of records to fetch
            deduplicate: Remove nearby duplicate points (default: True)
            distance_threshold_meters: Distance threshold for deduplication (default: 50m)
            use_trajectory_processing: Apply Kalman Filter processing (default: True)

        Returns:
            List of location data points sorted by timestamp, cleaned and processed

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
                    "X-Organization": organization_slug,
                },
            )

            logger.info(
                f"Response status code: {response.status_code}, {organization_slug}"
            )

            if response.status_code == 404:
                logger.warning(f"404 - No location data found for device {device_id}")
                return []

            response.raise_for_status()

            data = response.json()
            locations = data.get("locations", [])
            logger.info(f"Received {len(locations)} raw locations")

            formatted_locations: list[LocationPoint] = []
            for loc in locations:
                formatted_locations.append(
                    LocationPoint(
                        timestamp=_parse_timestamp(loc.get("timestamp", "")),
                        latitude=loc.get("latitude", 0),
                        longitude=loc.get("longitude", 0),
                        device_id=device_id,
                    )
                )

            # Apply deduplication if requested
            if deduplicate and formatted_locations:
                formatted_locations = self._deduplicate_locations(
                    formatted_locations, distance_threshold_meters
                )
                logger.info(
                    f"After deduplication: {len(formatted_locations)} locations"
                )

            # Apply Kalman Filter trajectory processing
            if use_trajectory_processing and len(formatted_locations) >= 2:
                processor = KalmanFilterProcessor()
                formatted_locations = processor.process_trajectory(
                    formatted_locations, device_id
                )
                logger.info(
                    f"After Kalman processing: {len(formatted_locations)} locations "
                    f"(compression ratio: {len(data.get('locations', [])) / max(len(formatted_locations), 1):.2f}x)"
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
        self, device_id: str, organization_slug: str, space_slug: str
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
            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Organization": organization_slug,
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

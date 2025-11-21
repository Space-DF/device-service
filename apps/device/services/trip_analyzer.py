"""
Trip Analyzer Service
Analyzes device location data to detect and manage trips based on movement patterns
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple
from math import radians, cos, sin, asin, sqrt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import pytz

from apps.device.models import Trip, SpaceDevice
from apps.utils.clients.telemetry_client import TelemetryServiceClient, LocationPoint

logger = logging.getLogger(__name__)


@dataclass
class TripWithLocations:
    """Data class for trip with location points"""
    id: str
    space_device_id: str
    started_at: str
    is_finished: bool
    checkpoints: List[LocationPoint]
    location_count: int


class TripAnalyzerService:
    """
    Service for analyzing device location data and detecting trips

    Trip detection rules:
    - A new trip is created when movement is detected after a stop
    - A trip ends when device stops for >= STOP_TIME_THRESHOLD and then moves again
    - Stops are detected when distance < STOP_DISTANCE_THRESHOLD
    - Movement is detected when distance > MOVE_DISTANCE_THRESHOLD
    """

    def __init__(self):
        """Initialize the trip analyzer with configuration from settings"""
        self.telemetry_client = TelemetryServiceClient()

        self.stop_distance_meters = getattr(settings, 'TRIP_STOP_DISTANCE_METERS', 50)
        self.stop_time_minutes = getattr(settings, 'TRIP_STOP_TIME_MINUTES', 5)
        self.move_distance_meters = getattr(settings, 'TRIP_MOVE_DISTANCE_METERS', 100)

        logger.info(
            f"TripAnalyzer initialized with: "
            f"stop_distance={self.stop_distance_meters}m, "
            f"stop_time={self.stop_time_minutes}min, "
            f"move_distance={self.move_distance_meters}m"
        )

    def analyze_and_update_current_trip(self,
                                        space_device: SpaceDevice,
                                        current_trip: Trip | None = None):
        device_id = str(space_device.device.id)
        if not current_trip:
            logger.info("No current unfinished trip found for device %s will create new one", device_id)
            organization_slug = space_device.space.slug_name
            logger.info(f"Organization slug: {organization_slug}")

            earliest_start = datetime(2020, 1, 1, tzinfo=pytz.UTC)
            locations = self.telemetry_client.get_location_history(
                device_id, organization_slug, earliest_start
            )
            logger.info(f"Telemetry response: \
                {len(locations) if locations else 0} locations found")
            logger.info(f"Locations: {locations}")
            if locations and len(locations) > 0:
                first_location = locations[0]
                logger.info(
                    "Creating trip: started_at=%s, lat=%s, lng=%s",
                    first_location.timestamp, first_location.latitude, first_location.longitude
                )
                current_trip = Trip.objects.create(
                    space_device=space_device,
                    started_at=first_location.timestamp,
                    is_finished=False,
                    last_latitude=first_location.latitude,
                    last_longitude=first_location.longitude,
                    last_report=first_location.timestamp
                )
                logger.info(
                    "Created trip with ID=%s using first location timestamp: %s",
                    current_trip.id, current_trip.started_at
                )
            else:
                # No location data exists yet, create trip with current time
                now = timezone.now()
                logger.info(f"No location history found, creating trip with current time: {now}")
                current_trip = Trip.objects.create(
                    space_device=space_device,
                    started_at=now,
                    is_finished=False
                )
                logger.info(f"Created trip with ID={current_trip.id} using current time")

        if not current_trip.last_report:
            logger.info(
                "Trip %s has no last_report, setting to started_at=%s",
                current_trip.id, current_trip.started_at
            )
            # Trip exists but no last report yet, set it to trip start time
            current_trip.last_report = current_trip.started_at
            current_trip.save(update_fields=['last_report'])
            logger.info(f"Updated trip {current_trip.id} last_report to {current_trip.last_report}")

        # Fetch locations since last report
        logger.info(f"Fetching new locations since last_report={current_trip.last_report}")
        new_locations = self.telemetry_client.get_location_history(
            device_id=str(space_device.device.id),
            organization_slug=space_device.space.slug_name,
            start=current_trip.last_report,
            end=None,  # Get all locations up to now
        )
        if not new_locations:
            logger.info("No new locations found, skipping analysis")
            return
        new_trips: list[Trip] = []
        save_current_trip_func = None
        for i, location in enumerate(new_locations):
            if current_trip.last_report >= location.timestamp:
                continue
            coords = (
                location.latitude,
                location.longitude
            )
            if not current_trip.last_latitude or not current_trip.last_longitude:
                current_trip.last_latitude, current_trip.last_longitude = coords
                current_trip.last_report = location.timestamp

            last_coords = (
                current_trip.last_latitude,
                current_trip.last_longitude
            )
            time_diff = (location.timestamp - current_trip.last_report).total_seconds() / 60

            distance = self._calculate_distance(last_coords, coords)
            is_stopped = distance < self.stop_distance_meters

            if is_stopped and time_diff >= self.stop_time_minutes:
                logger.info(
                    "Device stopped for %.2f minutes (threshold: %d), checking for next movement",
                    time_diff, self.stop_time_minutes
                )
                next_loc = new_locations[i+1] if i + 1 < len(new_locations) else None
                if not next_loc:
                    logger.info("No next location to check for movement, ending analysis")
                    break

                next_coords = (
                    next_loc.latitude,
                    next_loc.longitude
                )
                next_distance = self._calculate_distance(coords, next_coords)
                if next_distance < self.move_distance_meters:
                    logger.info(
                        "Next location distance %.2fm is below move threshold %.2fm, continuing stop",
                        next_distance, self.move_distance_meters
                    )
                    current_trip.last_report = next_loc.timestamp
                    current_trip.last_latitude = next_loc.latitude
                    current_trip.last_longitude = next_loc.longitude
                    continue
                logger.info("Device moved again, ending trip started at %s", current_trip.started_at)
                current_trip.is_finished = True
                new_trip = Trip(
                    space_device=space_device,
                    started_at=next_loc.timestamp,
                    is_finished=False,
                    last_latitude=next_coords[0],
                    last_longitude=next_coords[1],
                    last_report=next_loc.timestamp
                )
                new_trips.append(new_trip)
                if current_trip.id:  # already in DB if not then it's already in new_trips
                    save_current_trip_func = current_trip.save
                current_trip = new_trip
            else:
                # Update current trip last location and report time
                logger.info(
                    "Updating current trip %s last location to lat=%s, lng=%s at %s",
                    current_trip.id, location.latitude, location.longitude, location.timestamp)
                current_trip.last_latitude = location.latitude
                current_trip.last_longitude = location.longitude
                current_trip.last_report = location.timestamp
                current_trip.save(update_fields=['last_latitude', 'last_longitude', 'last_report'])

        logger.info(f"Found {len(new_trips)} new trips, saving...")
        with transaction.atomic():
            if save_current_trip_func:
                save_current_trip_func()
            if new_trips:
                Trip.objects.bulk_create(new_trips)

    def _calculate_distance(
        self,
        coord1: Tuple[float, float],
        coord2: Tuple[float, float]
    ) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula

        Args:
            coord1: (latitude, longitude) tuple
            coord2: (latitude, longitude) tuple

        Returns:
            Distance in meters
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # Radius of Earth in meters
        R = 6371000

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        return R * c

    def get_trip_with_locations(
        self,
        trip: Trip,
        organization_slug: str
    ) -> TripWithLocations:
        """
        Get a trip with its associated location points from telemetry service

        Args:
            trip: Trip model instance
            organization_slug: Organization slug

        Returns:
            TripWithLocations data class with trip data and location points
        """
        device_id = str(trip.space_device.device.id)

        # Fetch locations for the trip time range
        raw_locations = self.telemetry_client.get_location_history(
            device_id=device_id,
            organization_slug=organization_slug,
            start=trip.started_at,
            end=trip.last_report if trip.is_finished else None,
            limit=10000
        )

        # Convert raw location dicts to LocationPoint objects
        location_points = []
        for loc in raw_locations:
            location_points.append(LocationPoint(
                timestamp=loc.timestamp,
                latitude=loc.latitude,
                longitude=loc.longitude,
                accuracy=loc.accuracy,
                device_id=device_id,
            ))

        return TripWithLocations(
            id=str(trip.id),
            space_device_id=str(trip.space_device.id),
            started_at=trip.started_at.isoformat(),
            is_finished=trip.is_finished,
            checkpoints=location_points,
            location_count=len(location_points)
        )

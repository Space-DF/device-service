"""
Trip Analyzer Service
Analyzes device location data to detect and manage trips based on movement patterns
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import List, Tuple

import pytz
from django.conf import settings
from django.db import transaction

from apps.device.models import SpaceDevice, Trip
from apps.utils.clients.telemetry_client import LocationPoint, TelemetryServiceClient

logger = logging.getLogger(__name__)


@dataclass
class TripWithLocations:
    id: str
    space_device_id: str
    started_at: str
    is_finished: bool
    checkpoints: List[LocationPoint]
    location_count: int


class TripAnalyzerService:
    """
    Trip rules (according to new requirement):

    - Trip = the time period the device MOVES continuously.
    - If the device is stationary (distance between points < STOP_DISTANCE)
    for at least STOP_TIME_MINUTES, then moves >= MOVE_DISTANCE
    then cut the trip: end the old trip, create a new trip.
    - Lost connection / out of battery / offline does not automatically create a new trip.
    """

    def __init__(self):
        """Initialize the trip analyzer with configuration from settings"""
        self.telemetry_client = TelemetryServiceClient()

        self.stop_distance_meters = getattr(settings, "TRIP_STOP_DISTANCE_METERS", 50)
        self.stop_time_minutes = getattr(settings, "TRIP_STOP_TIME_MINUTES", 5)
        self.move_distance_meters = getattr(settings, "TRIP_MOVE_DISTANCE_METERS", 100)

        logger.info(
            f"TripAnalyzer initialized with: "
            f"stop_distance={self.stop_distance_meters}m, "
            f"stop_time={self.stop_time_minutes}min, "
            f"move_distance={self.move_distance_meters}m"
        )

    def analyze_and_update_current_trip(
        self,
        organization_slug: str,
        space_device: SpaceDevice,
        current_trip: Trip | None = None,
    ):
        device_id = str(space_device.device.id)
        space_slug = space_device.space.slug_name

        logger.info(
            "Analyze trips for device=%s, space=%s, current_trip=%s",
            device_id,
            space_slug,
            current_trip.id if current_trip else None,
        )

        # Make sure to have current_trip if there is a historical location
        current_trip = self._ensure_current_trip(
            organization_slug, space_device, current_trip
        )
        if not current_trip:
            logger.info(
                "No trip and no location history for device=%s, skip analysis",
                device_id,
            )
            return

        # Get locations newer than last_report
        if not current_trip.last_report:
            current_trip.last_report = current_trip.started_at
            current_trip.save(update_fields=["last_report"])

        analysis_start = current_trip.last_report
        overlap_minutes = self.stop_time_minutes + 1
        start_time = analysis_start - timedelta(minutes=overlap_minutes)

        if start_time < current_trip.started_at:
            start_time = current_trip.started_at

        logger.info("Fetching locations for device=%s since %s", device_id, start_time)

        new_locations: list[LocationPoint] = self.telemetry_client.get_location_history(
            device_id=device_id,
            organization_slug=organization_slug,
            space_slug=space_slug,
            start=start_time,
            end=None,
        )

        if not new_locations:
            logger.info("No new locations for device=%s, nothing to update", device_id)
            return

        new_locations.sort(key=lambda item: item.timestamp)

        with transaction.atomic():
            self._process_locations_for_trip(
                space_device=space_device,
                current_trip=current_trip,
                new_locations=new_locations,
                analysis_start=analysis_start,
            )

    def _process_locations_for_trip(
        self,
        space_device: SpaceDevice,
        current_trip: Trip,
        new_locations: list[LocationPoint],
        analysis_start: datetime,
    ):
        """
        Simple device state:

        - prev_time / prev_coords: previous point processed.
        - stop_start_time / stop_ref_coords: start time and position of "stand still" sequence.
        - in_long_stop = True when stand still >= stop_time_minutes.
        - Only when in_long_stop=True and moved_from_stop >= move_distance
        will cut trip and create new trip.
        """
        prev_time: datetime | None = None
        prev_coords: Tuple[float, float] | None = None

        stop_start_time: datetime | None = None
        stop_ref_coords: Tuple[float, float] | None = None
        in_long_stop = False

        new_trips: list[Trip] = []

        for loc in new_locations:
            coords = (loc.latitude, loc.longitude)
            is_new = loc.timestamp > analysis_start

            if prev_coords is None:
                prev_coords = coords
                prev_time = loc.timestamp

                if is_new:
                    current_trip.last_latitude = loc.latitude
                    current_trip.last_longitude = loc.longitude
                    current_trip.last_report = loc.timestamp

                continue

            distance = self._calculate_distance(prev_coords, coords)
            time_diff_min = (loc.timestamp - prev_time).total_seconds() / 60.0

            logger.info(
                "Device %s step: dt=%.2fmin, d=%.2fm, prev=%s, curr=%s",
                space_device.device_id,
                time_diff_min,
                distance,
                prev_coords,
                coords,
            )

            # Device is stationary
            if distance <= self.stop_distance_meters:
                if stop_start_time is None:
                    stop_start_time = prev_time
                    stop_ref_coords = prev_coords

                stop_duration_min = (
                    loc.timestamp - stop_start_time
                ).total_seconds() / 60.0

                if stop_duration_min >= self.stop_time_minutes:
                    in_long_stop = True

                if is_new:
                    current_trip.last_latitude = loc.latitude
                    current_trip.last_longitude = loc.longitude
                    current_trip.last_report = loc.timestamp

                prev_coords = coords
                prev_time = loc.timestamp
                continue

            # Device is moving
            if in_long_stop and stop_ref_coords is not None:
                moved_from_stop = self._calculate_distance(stop_ref_coords, coords)
                logger.info(
                    "Device %s moved_from_stop=%.2fm (threshold=%sm)",
                    space_device.device_id,
                    moved_from_stop,
                    self.move_distance_meters,
                    is_new,
                )

                if is_new and moved_from_stop >= self.move_distance_meters:
                    current_trip.is_finished = True
                    current_trip.last_report = prev_time

                    if current_trip.pk:
                        current_trip.save(update_fields=["is_finished", "last_report"])

                    new_trip = Trip(
                        space_device=space_device,
                        started_at=prev_time,
                        is_finished=False,
                        last_latitude=loc.latitude,
                        last_longitude=loc.longitude,
                        last_report=loc.timestamp,
                    )
                    new_trips.append(new_trip)
                    current_trip = new_trip

                    # Reset stop state
                    stop_start_time = None
                    stop_ref_coords = None
                    in_long_stop = False

                    prev_coords = (loc.latitude, loc.longitude)
                    prev_time = loc.timestamp
                    continue

            if is_new:
                current_trip.last_latitude = loc.latitude
                current_trip.last_longitude = loc.longitude
                current_trip.last_report = loc.timestamp

            stop_start_time = None
            stop_ref_coords = None
            in_long_stop = False

            prev_coords = coords
            prev_time = loc.timestamp

        if current_trip.pk:
            current_trip.save(
                update_fields=[
                    "last_latitude",
                    "last_longitude",
                    "last_report",
                    "is_finished",
                ]
            )
        if new_trips:
            unsaved_trips = [trip for trip in new_trips if not trip.pk]
            if unsaved_trips:
                Trip.objects.bulk_create(unsaved_trips)

    def _ensure_current_trip(
        self,
        organization_slug: str,
        space_device: SpaceDevice,
        current_trip: Trip | None,
    ) -> Trip | None:
        """
        - If there is a current_trip -> use it now.
        - If there is no trip:
            + If there is a historical location -> create the first trip from the first location.
            + If there is no location -> return None (DO NOT create an empty trip).
        """
        if current_trip:
            return current_trip

        device_id = str(space_device.device.id)
        space_slug = space_device.space.slug_name

        earliest_start = datetime(2020, 1, 1, tzinfo=pytz.UTC)
        locations = self.telemetry_client.get_location_history(
            device_id=device_id,
            organization_slug=organization_slug,
            space_slug=space_slug,
            start=earliest_start,
            end=None,
        )

        if not locations:
            logger.info(
                "No location history for device=%s, will not create empty trip",
                device_id,
            )
            return None

        first_trip = sorted(locations, key=lambda item: item.timestamp)[0]
        logger.info(
            "Creating first trip for device=%s at %s (lat=%s, lng=%s)",
            device_id,
            first_trip.timestamp,
            first_trip.latitude,
            first_trip.longitude,
        )

        trip = Trip.objects.create(
            space_device=space_device,
            started_at=first_trip.timestamp,
            is_finished=False,
            last_latitude=first_trip.latitude,
            last_longitude=first_trip.longitude,
            last_report=first_trip.timestamp,
        )
        return trip

    def _calculate_distance(
        self, coord1: Tuple[float, float], coord2: Tuple[float, float]
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
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        return R * c

    def get_trip_with_locations(
        self, trip: Trip, organization_slug: str, space_slug: str
    ) -> TripWithLocations:
        """
        Get a trip with its associated location points from telemetry service

        Args:
            trip: Trip model instance
            space_slug: Organization slug

        Returns:
            TripWithLocations data class with trip data and location points
        """
        device_id = str(trip.space_device.device.id)

        # Fetch locations for the trip time range
        raw_locations = self.telemetry_client.get_location_history(
            device_id=device_id,
            organization_slug=organization_slug,
            space_slug=space_slug,
            start=trip.started_at,
            end=trip.last_report if trip.is_finished else None,
            limit=10000,
        )

        # Convert raw location dicts to LocationPoint objects
        location_points: list[LocationPoint] = []
        for loc in raw_locations:
            location_points.append(
                LocationPoint(
                    timestamp=loc.timestamp,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    device_id=device_id,
                )
            )

        return TripWithLocations(
            id=str(trip.id),
            space_device_id=str(trip.space_device.id),
            started_at=trip.started_at.isoformat(),
            is_finished=trip.is_finished,
            checkpoints=location_points,
            location_count=len(location_points),
        )

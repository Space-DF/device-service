"""
Trip Analyzer Service
Analyzes device location data to detect and manage trips based on movement patterns.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

import pytz
from common.utils.haversine_distance import haversine_distance
from common.utils.telemetry_client import LocationPoint, TelemetryServiceClient
from django.conf import settings
from django.db import transaction

from apps.device.models import SpaceDevice, Trip
from apps.device.services.filter_processor import FilterProcessor

logger = logging.getLogger(__name__)


@dataclass
class TripWithLocations:
    id: str
    space_device_id: str
    started_at: str
    is_finished: bool
    checkpoints: List[LocationPoint]
    location_count: int


@dataclass
class TripAnalysisContext:
    current_trip: Trip | None
    analysis_start: datetime | None
    start_time: datetime


@dataclass
class ResolvedTripAnalysis:
    current_trip: Trip | None
    analysis_start: datetime | None
    new_locations: list[LocationPoint]


@dataclass
class TripProcessingState:
    current_trip: Trip | None
    trip_locations: list[LocationPoint]
    pending_trip_locations: list[LocationPoint]
    pending_anchor_location: LocationPoint | None = None
    prev_time: datetime | None = None
    prev_coords: Tuple[float, float] | None = None
    stop_start_time: datetime | None = None
    stop_ref_coords: Tuple[float, float] | None = None


class TripAnalyzerService:
    def __init__(self):
        self.telemetry_client = TelemetryServiceClient()
        self.filter_processor = FilterProcessor()

        self.min_valid_trip_points = getattr(settings, "TRIP_MIN_LOCATION_COUNT", 2)
        self.stop_distance_meters = getattr(settings, "TRIP_STOP_DISTANCE_METERS", 50)
        self.stop_time_minutes = getattr(settings, "TRIP_STOP_TIME_MINUTES", 5)
        self.offline_split_minutes = getattr(settings, "TRIP_OFFLINE_SPLIT_MINUTES", 10)

        logger.info(
            "TripAnalyzer initialized with: min_valid_points>%s, "
            "stop_distance=%sm, stop_time=%smin, offline_split=%smin",
            self.min_valid_trip_points,
            self.stop_distance_meters,
            self.stop_time_minutes,
            self.offline_split_minutes,
        )

    def analyze_and_update_current_trip(
        self,
        organization_slug: str,
        space_device: SpaceDevice,
        current_trip: Trip | None = None,
    ):
        device_id = str(space_device.device.id)
        space_slug = space_device.space.slug_name

        context = self._build_analysis_context(space_device, current_trip)

        new_locations = self._fetch_preprocessed_locations(
            organization_slug=organization_slug,
            space_slug=space_slug,
            device_id=device_id,
            start_time=context.start_time,
        )

        if not new_locations:
            logger.debug("No new locations for device=%s, nothing to update", device_id)
            return

        with transaction.atomic():
            space_device = SpaceDevice.objects.select_for_update().get(
                pk=space_device.pk
            )
            current_trip = self._get_locked_current_trip(space_device, current_trip)
            context = self._build_analysis_context(space_device, current_trip)

            if current_trip and context.analysis_start is None:
                return

            self._process_locations_for_trip(
                space_device=space_device,
                current_trip=current_trip,
                new_locations=new_locations,
                analysis_start=context.analysis_start,
            )

    def _get_locked_current_trip(
        self,
        space_device: SpaceDevice,
        current_trip: Trip | None,
    ) -> Trip | None:
        if current_trip:
            return Trip.objects.select_for_update().filter(pk=current_trip.pk).first()

        return (
            Trip.objects.select_for_update()
            .filter(space_device=space_device, is_finished=False)
            .order_by("-started_at")
            .first()
        )

    def _build_analysis_context(
        self,
        space_device: SpaceDevice,
        current_trip: Trip | None,
    ) -> TripAnalysisContext:
        if current_trip:
            return self._build_existing_trip_context(current_trip)

        latest_trip = (
            Trip.objects.filter(space_device=space_device)
            .order_by("-last_report", "-started_at")
            .first()
        )
        analysis_start = latest_trip.last_report if latest_trip else None
        start_time = analysis_start or datetime(2020, 1, 1, tzinfo=pytz.UTC)

        return TripAnalysisContext(
            current_trip=None,
            analysis_start=analysis_start,
            start_time=start_time,
        )

    def _build_existing_trip_context(self, current_trip: Trip) -> TripAnalysisContext:
        if not current_trip.last_report:
            current_trip.last_report = current_trip.started_at
            current_trip.save(update_fields=["last_report"])

        analysis_start = current_trip.last_report
        overlap_minutes = self.stop_time_minutes + 1
        start_time = analysis_start - timedelta(minutes=overlap_minutes)

        if start_time < current_trip.started_at:
            start_time = current_trip.started_at

        return TripAnalysisContext(
            current_trip=current_trip,
            analysis_start=analysis_start,
            start_time=start_time,
        )

    def _fetch_preprocessed_locations(
        self,
        organization_slug: str,
        space_slug: str,
        device_id: str,
        start_time: datetime,
    ) -> list[LocationPoint]:
        logger.info("Fetching locations for device=%s since %s", device_id, start_time)

        locations: list[LocationPoint] = self.telemetry_client.get_location_history(
            device_id=device_id,
            organization_slug=organization_slug,
            space_slug=space_slug,
            start=start_time,
            end=None,
        )

        if not locations:
            return []

        if len(locations) < 2:
            return locations

        return self.filter_processor.filter_outliers(locations)

    def _process_locations_for_trip(
        self,
        space_device: SpaceDevice,
        current_trip: Trip | None,
        new_locations: list[LocationPoint],
        analysis_start: datetime | None,
    ):
        offline_split_delta = timedelta(minutes=self.offline_split_minutes)
        logger.debug(
            "Process locations for device=%s current_trip=%s analysis_start=%s total_points=%s",
            space_device.device_id,
            current_trip.id if current_trip else None,
            analysis_start,
            len(new_locations),
        )
        state = TripProcessingState(
            current_trip=current_trip,
            trip_locations=[],
            pending_trip_locations=[],
        )

        for loc in new_locations:
            coords = (loc.latitude, loc.longitude)
            is_new = analysis_start is None or loc.timestamp > analysis_start
            logger.debug(
                "Processing point for device=%s timestamp=%s coords=%s is_new=%s "
                "current_trip=%s pending_points=%s trip_points=%s",
                space_device.device_id,
                loc.timestamp,
                coords,
                is_new,
                state.current_trip.id if state.current_trip else None,
                len(state.pending_trip_locations),
                len(state.trip_locations),
            )

            if self._handle_first_location_case(
                state,
                space_device,
                loc,
                coords,
                is_new,
            ):
                continue

            gap = loc.timestamp - state.prev_time
            logger.debug(
                "Device %s step: gap=%.2fmin, prev_time=%s, curr_time=%s",
                space_device.device_id,
                gap.total_seconds() / 60.0,
                state.prev_time,
                loc.timestamp,
            )

            if state.current_trip is None:
                if is_new and gap > offline_split_delta:
                    state.pending_trip_locations = []
                    state.pending_anchor_location = None
                    self._reset_stop_state(state)
                self._handle_pending_trip_case(state, space_device, loc, is_new)
                self._advance_trip_processing_cursor(state, loc.timestamp, coords)
                continue

            if self._handle_offline_gap_case(
                state=state,
                loc=loc,
                coords=coords,
                is_new=is_new,
                gap=gap,
                offline_split_delta=offline_split_delta,
            ):
                continue

            step_distance = haversine_distance(
                state.prev_coords[0],
                state.prev_coords[1],
                coords[0],
                coords[1],
            )

            stationary_distance = step_distance
            if state.stop_ref_coords is not None:
                stationary_distance = haversine_distance(
                    state.stop_ref_coords[0],
                    state.stop_ref_coords[1],
                    coords[0],
                    coords[1],
                )

            logger.debug(
                "Device %s step_distance=%.2fm stationary_distance=%.2fm, "
                "prev_coords=%s, curr_coords=%s",
                space_device.device_id,
                step_distance,
                stationary_distance,
                state.prev_coords,
                coords,
            )

            if self._handle_stationary_case(
                state=state,
                space_device=space_device,
                loc=loc,
                coords=coords,
                is_new=is_new,
                stationary_distance=stationary_distance,
            ):
                continue

            self._handle_active_trip_movement_case(state, loc, is_new)
            self._reset_stop_state(state)
            self._advance_trip_processing_cursor(state, loc.timestamp, coords)

        self._save_processed_trip(state)
        logger.error(
            "Finished processing device=%s current_trip=%s pending_points=%s trip_points=%s",
            space_device.device_id,
            state.current_trip.id if state.current_trip else None,
            len(state.pending_trip_locations),
            len(state.trip_locations),
        )

    def _handle_first_location_case(
        self,
        state: TripProcessingState,
        space_device: SpaceDevice,
        loc: LocationPoint,
        coords: Tuple[float, float],
        is_new: bool,
    ) -> bool:
        if state.prev_time is not None and state.prev_coords is not None:
            return False

        state.prev_time = loc.timestamp
        state.prev_coords = coords

        if state.current_trip is None:
            if is_new:
                logger.error(
                    "First point buffered for device=%s timestamp=%s coords=%s",
                    space_device.device_id,
                    loc.timestamp,
                    coords,
                )
                self._append_trip_location(state.pending_trip_locations, loc)
                self._try_create_trip_from_pending(state, space_device)
            return True

        state.trip_locations.append(loc)

        if is_new and not state.current_trip.is_finished:
            self._update_trip_last_point(state.current_trip, loc)

        return True

    def _handle_offline_gap_case(
        self,
        state: TripProcessingState,
        loc: LocationPoint,
        coords: Tuple[float, float],
        is_new: bool,
        gap: timedelta,
        offline_split_delta: timedelta,
    ) -> bool:
        if state.current_trip is None:
            return False

        if not (
            is_new and gap > offline_split_delta and not state.current_trip.is_finished
        ):
            return False

        finished = self._finish_trip(
            trip=state.current_trip,
            trip_locations=state.trip_locations,
            finished_at=state.prev_time,
            latitude=state.prev_coords[0],
            longitude=state.prev_coords[1],
            reason="offline_gap",
        )
        if finished:
            state.current_trip = None
            state.trip_locations = []
            state.pending_trip_locations = [loc] if is_new else []
            state.pending_anchor_location = None
            self._reset_stop_state(state)
        self._advance_trip_processing_cursor(state, loc.timestamp, coords)
        return True

    def _handle_stationary_case(
        self,
        state: TripProcessingState,
        space_device: SpaceDevice,
        loc: LocationPoint,
        coords: Tuple[float, float],
        is_new: bool,
        stationary_distance: float,
    ) -> bool:
        if (
            state.current_trip is None
            or stationary_distance > self.stop_distance_meters
        ):
            return False

        if state.stop_start_time is None:
            state.stop_start_time = state.prev_time
            state.stop_ref_coords = state.prev_coords

        stop_duration_min = (
            loc.timestamp - state.stop_start_time
        ).total_seconds() / 60.0
        logger.debug(
            "Device %s stationary for %.2fmin",
            space_device.device_id,
            stop_duration_min,
        )

        if (
            is_new
            and not state.current_trip.is_finished
            and stop_duration_min >= self.stop_time_minutes
            and state.stop_ref_coords is not None
        ):
            finished = self._finish_trip(
                trip=state.current_trip,
                trip_locations=state.trip_locations,
                finished_at=state.stop_start_time,
                latitude=state.stop_ref_coords[0],
                longitude=state.stop_ref_coords[1],
                reason="stationary_timeout",
            )
            if finished:
                state.current_trip = None
                state.trip_locations = []
                state.pending_trip_locations = []
                state.pending_anchor_location = loc if is_new else None
                self._reset_stop_state(state)
            self._advance_trip_processing_cursor(state, loc.timestamp, coords)
            return True

        if is_new and not state.current_trip.is_finished:
            self._update_trip_last_point(state.current_trip, loc)

        self._advance_trip_processing_cursor(state, loc.timestamp, coords)
        return True

    def _handle_pending_trip_case(
        self,
        state: TripProcessingState,
        space_device: SpaceDevice,
        loc: LocationPoint,
        is_new: bool,
    ) -> None:
        if not is_new:
            return

        if (
            state.pending_anchor_location is not None
            and not state.pending_trip_locations
        ):
            anchor_distance = haversine_distance(
                state.pending_anchor_location.latitude,
                state.pending_anchor_location.longitude,
                loc.latitude,
                loc.longitude,
            )
            if anchor_distance <= self.stop_distance_meters:
                logger.debug(
                    "Pending anchor retained for device=%s timestamp=%s "
                    "anchor_timestamp=%s anchor_distance=%.2fm threshold=%.2fm",
                    space_device.device_id,
                    loc.timestamp,
                    state.pending_anchor_location.timestamp,
                    anchor_distance,
                    self.stop_distance_meters,
                )
                return

            logger.info(
                "Pending anchor promoted for device=%s anchor_timestamp=%s "
                "movement_timestamp=%s anchor_distance=%.2fm",
                space_device.device_id,
                state.pending_anchor_location.timestamp,
                loc.timestamp,
                anchor_distance,
            )
            self._append_trip_location(
                state.pending_trip_locations,
                state.pending_anchor_location,
            )
            state.pending_anchor_location = None

        logger.info(
            "Appending pending point for device=%s timestamp=%s pending_points_before=%s",
            space_device.device_id,
            loc.timestamp,
            len(state.pending_trip_locations),
        )
        self._append_trip_location(state.pending_trip_locations, loc)
        logger.info(
            "Pending buffer updated for device=%s pending_points_after=%s",
            space_device.device_id,
            len(state.pending_trip_locations),
        )
        self._try_create_trip_from_pending(state, space_device)

    def _handle_active_trip_movement_case(
        self,
        state: TripProcessingState,
        loc: LocationPoint,
        is_new: bool,
    ) -> None:
        if state.current_trip is None or not (
            is_new and not state.current_trip.is_finished
        ):
            return

        if (
            not state.trip_locations
            or state.trip_locations[-1].timestamp != loc.timestamp
        ):
            state.trip_locations.append(loc)
        self._update_trip_last_point(state.current_trip, loc)

    def _reset_stop_state(self, state: TripProcessingState) -> None:
        state.stop_start_time = None
        state.stop_ref_coords = None

    def _advance_trip_processing_cursor(
        self,
        state: TripProcessingState,
        timestamp: datetime,
        coords: Tuple[float, float],
    ) -> None:
        state.prev_time = timestamp
        state.prev_coords = coords

    def _save_processed_trip(self, state: TripProcessingState) -> None:
        if state.current_trip is not None and state.current_trip.pk:
            state.current_trip.save(
                update_fields=[
                    "last_latitude",
                    "last_longitude",
                    "last_report",
                    "is_finished",
                ]
            )

    def _finish_trip(
        self,
        trip: Trip,
        trip_locations: list[LocationPoint],
        finished_at: datetime,
        latitude: float,
        longitude: float,
        reason: str,
    ) -> bool:
        """
        Finish a trip safely without changing DB model.

        finished_at:
            Real trip end time. This is used for metrics and logs only.
        """
        is_valid = trip.pk is not None or self._validate_trip(trip_locations)

        logger.info(
            "Finished trip=%s finished_at=%s reason=%s "
            "lat=%s lng=%s valid=%s persisted=%s buffered_locations=%s",
            trip.id if trip.pk else None,
            finished_at,
            reason,
            latitude,
            longitude,
            is_valid,
            trip.pk is not None,
            len(trip_locations),
        )

        if not is_valid:
            return False

        trip.is_finished = True
        trip.last_report = finished_at
        trip.last_latitude = latitude
        trip.last_longitude = longitude

        if trip.pk:
            trip.save(
                update_fields=[
                    "is_finished",
                    "last_report",
                    "last_latitude",
                    "last_longitude",
                ]
            )
        return is_valid

    def _update_trip_last_point(self, trip: Trip, location: LocationPoint):
        trip.last_latitude = location.latitude
        trip.last_longitude = location.longitude
        trip.last_report = location.timestamp

    def _validate_trip(self, trip_locations: list[LocationPoint]) -> bool:
        if len(trip_locations) < 2:
            logger.info(
                "Trip validation skipped: buffered_points=%s reason=too_few_points",
                len(trip_locations),
            )
            return False

        compressed_locations = self.filter_processor.compress_trajectory(trip_locations)
        is_valid = len(compressed_locations) >= self.min_valid_trip_points
        logger.info(
            "Trip validation: buffered_points=%s compressed_points=%s "
            "min_valid_trip_points=%s comparator='>=' valid=%s",
            len(trip_locations),
            len(compressed_locations),
            self.min_valid_trip_points,
            is_valid,
        )
        return is_valid

    def _append_trip_location(
        self, trip_locations: list[LocationPoint], location: LocationPoint
    ) -> None:
        if not trip_locations:
            trip_locations.append(location)
            logger.debug(
                "Buffered point appended timestamp=%s coords=(%s, %s) total_points=%s",
                location.timestamp,
                location.latitude,
                location.longitude,
                len(trip_locations),
            )
            return

        last = trip_locations[-1]
        if (
            last.timestamp == location.timestamp
            and last.latitude == location.latitude
            and last.longitude == location.longitude
        ):
            logger.debug(
                "Buffered point skipped as duplicate timestamp=%s coords=(%s, %s)",
                location.timestamp,
                location.latitude,
                location.longitude,
            )
            return
        trip_locations.append(location)
        logger.debug(
            "Buffered point appended timestamp=%s coords=(%s, %s) total_points=%s",
            location.timestamp,
            location.latitude,
            location.longitude,
            len(trip_locations),
        )

    def _try_create_trip_from_pending(
        self,
        state: TripProcessingState,
        space_device: SpaceDevice,
    ) -> None:
        if not self._validate_trip(state.pending_trip_locations):
            logger.debug(
                "Trip not created for device=%s pending_points=%s",
                space_device.device_id,
                len(state.pending_trip_locations),
            )
            return

        first_location = state.pending_trip_locations[0]
        last_location = state.pending_trip_locations[-1]
        state.current_trip = Trip.objects.create(
            space_device=space_device,
            started_at=first_location.timestamp,
            is_finished=False,
            last_latitude=last_location.latitude,
            last_longitude=last_location.longitude,
            last_report=last_location.timestamp,
        )
        logger.info(
            "Trip created for device=%s trip_id=%s started_at=%s buffered_points=%s",
            space_device.device_id,
            state.current_trip.id,
            first_location.timestamp,
            len(state.pending_trip_locations),
        )
        state.trip_locations = list(state.pending_trip_locations)
        state.pending_trip_locations = []
        state.pending_anchor_location = None

    def get_trip_with_locations(
        self,
        trip: Trip,
        organization_slug: str,
        space_slug: str,
    ) -> TripWithLocations:
        device_id = str(trip.space_device.device.id)

        raw_locations = self.telemetry_client.get_location_history(
            device_id=device_id,
            organization_slug=organization_slug,
            space_slug=space_slug,
            start=trip.started_at,
            end=trip.last_report,
            limit=10000,
        )

        if raw_locations:
            location_points = self.filter_processor.process_trajectory(
                raw_locations,
                device_id,
            )
        else:
            location_points = raw_locations

        return TripWithLocations(
            id=str(trip.id),
            space_device_id=str(trip.space_device.id),
            started_at=trip.started_at.isoformat(),
            is_finished=trip.is_finished,
            checkpoints=location_points,
            location_count=len(location_points),
        )

import logging
import math
from typing import List

from common.utils.haversine_distance import haversine_distance

from apps.device.constants import (
    DEFAULT_COMPRESSION_EPSILON_METERS,
    DEFAULT_MAX_SPEED_KMH,
    DEFAULT_MIN_POINT_DISTANCE_METERS,
    LocationPoint,
)

logger = logging.getLogger(__name__)


class FilterProcessor:
    """
    Pure Python Filter for GPS trajectory smoothing.
    Combines outlier filtering, deduplication, trajectory compression,
    """

    def __init__(self):
        self.max_speed_kmh = DEFAULT_MAX_SPEED_KMH
        self.min_point_distance_meters = DEFAULT_MIN_POINT_DISTANCE_METERS
        self.compression_epsilon_meters = DEFAULT_COMPRESSION_EPSILON_METERS

    def process_trajectory(
        self, locations: List[LocationPoint], device_id: str
    ) -> List[LocationPoint]:
        """
        Process trajectory: filter outliers → deduplicate → compress.

        Optimal order:
        1. Filter outliers (impossible speeds)
        2. Deduplicate consecutive nearby points
        3. Compress with Douglas-Peucker (preserve shape before smoothing)
        """
        if len(locations) < 2:
            return locations

        filtered = self._filter_outliers(locations)
        if len(filtered) < 2:
            return filtered

        deduplicated = self._deduplicate_nearby_points(filtered)
        if len(deduplicated) < 2:
            return deduplicated

        compressed = self._compress_trajectory(deduplicated)
        if len(compressed) < 2:
            return compressed

        logger.debug(
            f"Device {device_id}: {len(locations)} → {len(filtered)} → "
            f"{len(deduplicated)} → {len(compressed)} points"
        )
        return compressed

    def filter_outliers(self, locations: List[LocationPoint]) -> List[LocationPoint]:
        return self._filter_outliers(locations)

    def compress_trajectory(
        self, locations: List[LocationPoint]
    ) -> List[LocationPoint]:
        return self._compress_trajectory(locations)

    def _filter_outliers(self, locations: List[LocationPoint]) -> List[LocationPoint]:
        if len(locations) < 2:
            return locations

        filtered = [locations[0]]

        for curr in locations[1:]:
            prev = filtered[-1]
            distance_m = haversine_distance(
                prev.latitude, prev.longitude, curr.latitude, curr.longitude
            )

            time_sec = (curr.timestamp - prev.timestamp).total_seconds()

            # Keep if speed is realistic (avoid division by zero)
            speed_kmh = (distance_m / time_sec * 3.6) if time_sec > 0 else 0

            if speed_kmh <= self.max_speed_kmh:
                filtered.append(curr)
            else:
                logger.debug(
                    f"Outlier removed: {speed_kmh:.1f} km/h (>{self.max_speed_kmh})"
                )

        return filtered

    def _deduplicate_nearby_points(
        self, locations: List[LocationPoint]
    ) -> List[LocationPoint]:
        """
        Remove consecutive nearby points.
        If a new point is within threshold of the last kept point,
        replace the old point with the newer point.
        """
        if len(locations) < 2:
            return locations

        deduplicated = [locations[0]]
        for curr in locations[1:]:
            prev = deduplicated[-1]

            distance_m = haversine_distance(
                prev.latitude,
                prev.longitude,
                curr.latitude,
                curr.longitude,
            )

            if distance_m > self.min_point_distance_meters:
                deduplicated.append(curr)
            else:
                logger.debug(
                    "Nearby old point replaced: distance=%.3fm threshold=%.3fm old_timestamp=%s new_timestamp=%s",
                    distance_m,
                    self.min_point_distance_meters,
                    prev.timestamp,
                    curr.timestamp,
                )
                deduplicated[-1] = curr

        return deduplicated

    def _compress_trajectory(
        self, locations: List[LocationPoint]
    ) -> List[LocationPoint]:
        """
        Remove collinear points using simplified Douglas-Peucker algorithm.

        Keep points that deviate significantly from straight line,
        remove intermediate points.
        """
        if len(locations) <= 2:
            return locations

        def _simplify(locs: List[LocationPoint], epsilon: float) -> List[LocationPoint]:
            """Recursive Douglas-Peucker simplification"""
            if len(locs) <= 2:
                return locs

            max_distance = 0
            max_idx = 0
            for i in range(1, len(locs) - 1):
                distance = self._point_to_line_distance(locs[0], locs[-1], locs[i])
                if distance > max_distance:
                    max_distance = distance
                    max_idx = i

            # If max distance > epsilon, recursively simplify
            if max_distance > epsilon:
                left = _simplify(locs[: max_idx + 1], epsilon)
                right = _simplify(locs[max_idx:], epsilon)
                return left[:-1] + right
            else:
                return [locs[0], locs[-1]]

        return _simplify(locations, self.compression_epsilon_meters)

    def _point_to_line_distance(
        self, point_a: LocationPoint, point_b: LocationPoint, point_c: LocationPoint
    ) -> float:
        """
        Calculate distance from point_c to segment AB in local projected meters.
        """
        ref_lat = point_a.latitude
        ref_lon = point_a.longitude

        ax, ay = 0.0, 0.0
        bx, by = self._project_to_local_meters(
            point_b.latitude, point_b.longitude, ref_lat, ref_lon
        )
        cx, cy = self._project_to_local_meters(
            point_c.latitude, point_c.longitude, ref_lat, ref_lon
        )

        abx = bx - ax
        aby = by - ay
        acx = cx - ax
        acy = cy - ay
        segment_length_sq = abx * abx + aby * aby

        if segment_length_sq <= 1e-9:
            return math.hypot(acx, acy)

        projection = (acx * abx + acy * aby) / segment_length_sq
        projection = max(0.0, min(1.0, projection))

        closest_x = ax + projection * abx
        closest_y = ay + projection * aby
        return math.hypot(cx - closest_x, cy - closest_y)

    def _project_to_local_meters(
        self,
        latitude: float,
        longitude: float,
        ref_latitude: float,
        ref_longitude: float,
    ) -> tuple[float, float]:
        earth_radius_m = 6371000.0
        lat_rad = math.radians(latitude)
        lon_rad = math.radians(longitude)
        ref_lat_rad = math.radians(ref_latitude)
        ref_lon_rad = math.radians(ref_longitude)

        x = (lon_rad - ref_lon_rad) * math.cos((lat_rad + ref_lat_rad) / 2.0)
        y = lat_rad - ref_lat_rad
        return earth_radius_m * x, earth_radius_m * y

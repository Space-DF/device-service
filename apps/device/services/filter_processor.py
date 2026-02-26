import logging
from typing import List

from common.utils.haversine_distance import haversine_distance

from apps.device.constants import (
    DEFAULT_MAX_SPEED_KMH,
    DEFAULT_MIN_POINT_DISTANCE,
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
        self.min_point_distance = DEFAULT_MIN_POINT_DISTANCE

    def process_trajectory(
        self, locations: List[LocationPoint], device_id: str
    ) -> List[LocationPoint]:
        """
        Process trajectory: filter outliers → deduplicate → compress.

        Optimal order:
        1. Filter outliers (impossible speeds)
        2. Deduplicate consecutive identical points
        3. Compress with Douglas-Peucker (preserve shape before smoothing)
        """
        if len(locations) < 2:
            return locations

        filtered = self._filter_outliers(locations)
        if len(filtered) < 2:
            return filtered

        deduplicated = self._deduplicate_identical_points(filtered)
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

    def _deduplicate_identical_points(
        self, locations: List[LocationPoint]
    ) -> List[LocationPoint]:
        """
        Remove consecutive points with identical coordinates.
        Keeps the first occurrence of each consecutive group of identical locations.
        """
        if len(locations) < 2:
            return locations

        deduplicated = [locations[0]]
        for curr in locations[1:]:
            prev = deduplicated[-1]
            if curr.latitude != prev.latitude or curr.longitude != prev.longitude:
                deduplicated.append(curr)
            else:
                logger.debug(f"Duplicate removed: ({curr.latitude}, {curr.longitude})")

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

        return _simplify(locations, self.min_point_distance)

    def _point_to_line_distance(
        self, point_a: LocationPoint, point_b: LocationPoint, point_c: LocationPoint
    ) -> float:
        """
        Calculate perpendicular distance from point_c to line AB (in meters).

        Uses Haversine distance for accurate great-circle calculation.
        """
        # Calculate distances using Haversine formula
        dist_ac = haversine_distance(
            point_a.latitude, point_a.longitude, point_c.latitude, point_c.longitude
        )
        dist_bc = haversine_distance(
            point_b.latitude, point_b.longitude, point_c.latitude, point_c.longitude
        )
        dist_ab = haversine_distance(
            point_a.latitude, point_a.longitude, point_b.latitude, point_b.longitude
        )

        # If line segment is too short, return distance to point A
        if dist_ab < 1:
            return dist_ac

        # Calculate perpendicular distance using triangle area formula
        # area = 0.5 * base * height => height = 2*area / base
        s = (dist_ac + dist_bc + dist_ab) / 2
        area = (s * (s - dist_ac) * (s - dist_bc) * (s - dist_ab)) ** 0.5

        return max(0, 2 * area / dist_ab)

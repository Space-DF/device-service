import logging
from typing import List

from apps.device.constants import (
    DEFAULT_MAX_SPEED_KMH,
    DEFAULT_MEASUREMENT_NOISE,
    DEFAULT_MIN_POINT_DISTANCE,
    DEFAULT_PROCESS_NOISE,
    LocationPoint,
)
from apps.utils.haversine_distance import haversine_distance

logger = logging.getLogger(__name__)


class KalmanFilterProcessor:
    """
    Pure Python Kalman Filter for GPS trajectory smoothing.

    Pipeline:
    1. Filter outliers (impossible speeds based on max_speed_kmh)
    2. Smooth coordinates (1D Kalman filter + RTS smoother per coordinate)
    3. Compress trajectory (Douglas-Peucker simplification)
    """

    def __init__(self):
        self.process_noise = DEFAULT_PROCESS_NOISE
        self.measurement_noise = DEFAULT_MEASUREMENT_NOISE
        self.max_speed_kmh = DEFAULT_MAX_SPEED_KMH
        self.min_point_distance = DEFAULT_MIN_POINT_DISTANCE

    def process_trajectory(
        self, locations: List[LocationPoint], device_id: str
    ) -> List[LocationPoint]:
        """
        Process trajectory: filter outliers → compress → smooth.

        Optimal order:
        1. Filter outliers (impossible speeds)
        2. Compress with Douglas-Peucker (preserve shape before smoothing)
        3. Smooth with Kalman (remove remaining noise)
        """
        if len(locations) < 2:
            return locations

        filtered = self._filter_outliers(locations)
        if len(filtered) < 2:
            return filtered

        compressed = self._compress_trajectory(filtered)
        if len(compressed) < 2:
            return compressed

        smoothed = self._apply_kalman_smoothing(compressed)

        logger.debug(
            f"Device {device_id}: {len(locations)} → {len(filtered)} → "
            f"{len(compressed)} → {len(smoothed)} points"
        )
        return smoothed

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

    def _apply_kalman_smoothing(
        self, locations: List[LocationPoint]
    ) -> List[LocationPoint]:
        """
        Apply Kalman filter to smooth latitude and longitude coordinates.

        Uses 1D Kalman filter for each coordinate independently (lat and lon).
        Much simpler than multi-dimensional approach but still effective for GPS smoothing.
        """
        if len(locations) < 2:
            return locations

        # Apply 1D Kalman filter for latitude and longitude separately
        smoothed_lats = self._kalman_1d(
            [loc.latitude for loc in locations],
            self.process_noise,
            self.measurement_noise,
        )

        smoothed_lons = self._kalman_1d(
            [loc.longitude for loc in locations],
            self.process_noise,
            self.measurement_noise,
        )

        # Reconstruct locations with smoothed coordinates
        smoothed = []
        for i, loc in enumerate(locations):
            smoothed_loc = LocationPoint(
                timestamp=loc.timestamp,
                latitude=smoothed_lats[i],
                longitude=smoothed_lons[i],
                device_id=loc.device_id,
            )
            smoothed.append(smoothed_loc)

        return smoothed

    @staticmethod
    def _kalman_1d(
        measurements: List[float], process_noise: float, measurement_noise: float
    ) -> List[float]:
        """
        1D Kalman filter implementation.

        Assumes constant velocity model: x(t+1) = x(t) + v*dt

        Args:
            measurements: List of measured values
            process_noise: Process noise variance (Q)
            measurement_noise: Measurement noise variance (R)

        Returns:
            List of smoothed values
        """
        if not measurements:
            return []

        n = len(measurements)

        # Forward pass: Kalman filter
        x_prior = [0.0] * n
        x_posterior = [0.0] * n
        p_prior = [1.0] * n
        p_posterior = [1.0] * n

        # Initialize with first measurement
        x_posterior[0] = measurements[0]
        p_posterior[0] = measurement_noise

        for k in range(1, n):
            x_prior[k] = x_posterior[k - 1]
            p_prior[k] = p_posterior[k - 1] + process_noise

            innovation = measurements[k] - x_prior[k]
            innovation_cov = p_prior[k] + measurement_noise
            kalman_gain = p_prior[k] / innovation_cov

            x_posterior[k] = x_prior[k] + kalman_gain * innovation
            p_posterior[k] = (1 - kalman_gain) * p_prior[k]

        # Backward pass: RTS smoother (Rauch-Tung-Striebel)
        smoothed = [0.0] * n
        smoothed[-1] = x_posterior[-1]

        for k in range(n - 2, -1, -1):
            smoother_gain = (
                p_posterior[k] / p_prior[k + 1] if p_prior[k + 1] != 0 else 0
            )
            smoothed[k] = x_posterior[k] + smoother_gain * (
                smoothed[k + 1] - x_prior[k + 1]
            )

        return smoothed

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

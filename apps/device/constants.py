from dataclasses import dataclass
from datetime import datetime

# Telemetry Service Constants
DEFAULT_REQUEST_TIMEOUT = 30  # seconds
DEFAULT_HEALTH_CHECK_TIMEOUT = 5  # seconds
DEFAULT_DISTANCE_THRESHOLD = 50.0  # meters

# Kalman Filter Constants
DEFAULT_PROCESS_NOISE = 1e-4
DEFAULT_MEASUREMENT_NOISE = 25.0
DEFAULT_MAX_SPEED_KMH = 150.0
DEFAULT_MIN_POINT_DISTANCE = 10.0  # meters


@dataclass
class LocationPoint:
    """Data class for a single location point"""

    timestamp: datetime
    latitude: float
    longitude: float
    device_id: str

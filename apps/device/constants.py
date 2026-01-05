from dataclasses import dataclass
from datetime import datetime

# Filter Constants
DEFAULT_MAX_SPEED_KMH = 150.0
DEFAULT_MIN_POINT_DISTANCE = 10.0  # meters


@dataclass
class LocationPoint:
    """Data class for a single location point"""

    timestamp: datetime
    latitude: float
    longitude: float
    device_id: str

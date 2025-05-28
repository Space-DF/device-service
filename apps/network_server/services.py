from enum import Enum
from typing import List, Optional


class NetworkServer(str, Enum):
    TTN = "ttn"
    CHIRPSTACK = "chirpstack"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.title()) for tag in cls]


network_servers = {
    NetworkServer.TTN: {
        "name": "TTN",
        "logo": "https://avatars.githubusercontent.com/u/13333576",
        "description": "The Things Network",
        "connection_type": ["http_server", "mqtt_broker"],
    },
    NetworkServer.CHIRPSTACK: {
        "name": "Chirpstack",
        "logo": "https://www.chirpstack.de/assets/logo-blue.png",
        "description": "Chirpstack LoRaWAN",
        "connection_type": ["http_server", "mqtt_broker"],
    },
}


def get_network_servers(name: Optional[str] = None) -> List[dict]:
    result = [
        {
            "name": meta["name"],
            "logo": meta["logo"],
            "description": meta["description"],
            "connection_type": meta["connection_type"],
        }
        for _, meta in network_servers.items()
    ]
    if name:
        result = [ns for ns in result if ns["name"].lower() == name.lower()]
    return result

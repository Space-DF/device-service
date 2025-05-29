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
        "connection_types": ["http_server", "mqtt_broker"],
    },
    NetworkServer.CHIRPSTACK: {
        "name": "Chirpstack",
        "logo": "https://www.chirpstack.de/assets/logo-blue.png",
        "description": "Chirpstack LoRaWAN",
        "connection_types": ["http_server", "mqtt_broker"],
    },
}


def get_network_servers(name: Optional[str] = None) -> List[dict]:
    result = [
        {
            "name": network_server["name"],
            "logo": network_server["logo"],
            "description": network_server["description"],
            "connection_types": network_server["connection_types"],
        }
        for _, network_server in network_servers.items()
    ]
    if name:
        result = [
            network_server
            for network_server in result
            if name.lower() in network_server["name"].lower()
        ]
    return result

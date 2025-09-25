from apps.network_server.models import NetworkServer

network_servers = [
    {
        "name": "TTN",
        "logo": "https://avatars.githubusercontent.com/u/13333576",
        "description": "The Things Network",
        "connection_types": ["http_server", "mqtt_broker"],
    },
    {
        "name": "Chirpstack",
        "logo": "https://www.chirpstack.de/assets/logo-blue.png",
        "description": "Chirpstack",
        "connection_types": ["http_server"],
    },
    {
        "name": "Helium",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Helium_Network_logo_%282025%29.png",
        "description": "Helium",
        "connection_types": ["http_server"],
    },
]


def create_network_servers():
    list_data = [
        NetworkServer(
            name=network_server.get("name"),
            logo=network_server.get("logo", ""),
            description=network_server.get("description", ""),
            connection_types=network_server.get("connection_types") or [],
        )
        for network_server in network_servers
    ]
    NetworkServer.objects.bulk_create(list_data)

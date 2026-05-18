from apps.network_server.models import NetworkServer

network_servers = [
    {
        "name": "TTN",
        "logo": "ttn.png",
        "description": "The Things Network",
        "connection_types": ["http_server", "mqtt_broker"],
    },
    {
        "name": "Chirpstack",
        "logo": "chirp_stack.png",
        "description": "Chirpstack",
        "connection_types": ["http_server"],
    },
    {
        "name": "Helium",
        "logo": "helium.png",
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

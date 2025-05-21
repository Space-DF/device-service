from emqx.requests import EMQXRequest


def test_connect_mqtt(name, server, username, password):
    url = f"{EMQXRequest.EMQX_API_URL}/connectors_probe"
    payload = {
        "name": name,
        "server": server,
        "username": username,
        "password": password,
        "proto_ver": "v3",
        "type": "mqtt",
    }

    try:
        EMQXRequest().request_post(
            url,
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        return True
    except Exception:
        return None

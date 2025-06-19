from apps.device.services import delete_action_http
from emqx.requests import EMQXRequest


def test_connect_mqtt(name, server, username, password):
    url = f"{EMQXRequest.EMQX_API_URL}/connectors_probe"
    payload = {
        "name": name,
        "server": server,
        "username": username,
        "password": password,
        "proto_ver": "v3",
        "keepalive": "0s",
        "pool_size": 1,
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


def create_connector_mqtt(data):
    url = f"{EMQXRequest.EMQX_API_URL}/connectors"
    mqtt_config = data.get("device_mqtt_config")
    payload = {
        "bridge_mode": False,
        "clean_start": True,
        "description": "",
        "keepalive": "2s",
        "max_inflight": 32,
        "name": data.get("name"),
        "password": mqtt_config.get("password"),
        "pool_size": 1,
        "proto_ver": "v3",
        "resource_opts": {"health_check_interval": "15s", "start_timeout": "5s"},
        "retry_interval": "15s",
        "server": mqtt_config.get("mqtt_broker"),
        "ssl": {"enable": False, "verify": "verify_peer"},
        "type": "mqtt",
        "username": mqtt_config.get("username"),
    }

    try:
        response = EMQXRequest().request_post(
            url,
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        return response.json()
    except Exception:
        return None


def create_resource_mqtt(data):
    url = f"{EMQXRequest.EMQX_API_URL}/sources"
    payload = {
        "connector": data.get("name"),
        "description": "",
        "enable": True,
        "name": "resource_" + data.get("name"),
        "parameters": {"topic": "v3/+/devices/+/up", "qos": 1},
        "resource_opts": {"health_check_interval": "15s"},
        "type": "mqtt",
    }

    try:
        response = EMQXRequest().request_post(
            url,
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        return response.json()
    except Exception:
        return None


def create_rule_mqtt(data, action):
    url = f"{EMQXRequest.EMQX_API_URL}/rules"
    name_resource = "resource_" + data.get("name")
    name_action = "http:" + action.name
    payload = {
        "actions": [name_action],
        "description": "",
        "name": "rule_" + data.get("name"),
        "sql": f'SELECT\n  json_decode(payload) as payload\nFROM\n "$bridges/mqtt:{name_resource}"',  # nosec
    }

    try:
        response = EMQXRequest().request_post(
            url,
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        return response.json()
    except Exception:
        return None


def delete_connector_mqtt(connector_id):
    url = f"{EMQXRequest.EMQX_API_URL}/connectors/mqtt%3A{connector_id}"
    try:
        EMQXRequest().request_delete(
            url,
            headers={"Content-Type": "application/json"},
        )
        return True
    except Exception:
        return None


def delete_resource_mqtt(resource_id):
    url = f"{EMQXRequest.EMQX_API_URL}/sources/mqtt%3A{resource_id}"
    try:
        EMQXRequest().request_delete(
            url,
            headers={"Content-Type": "application/json"},
        )
        return True
    except Exception:
        return None


def delete_rule_mqtt(rule_id):
    url = f"{EMQXRequest.EMQX_API_URL}/rules/{rule_id}"
    try:
        EMQXRequest().request_delete(
            url,
            headers={"Content-Type": "application/json"},
        )
        return True
    except Exception:
        return None


def get_rule(rule_id):
    url = f"{EMQXRequest.EMQX_API_URL}/rules/{rule_id}"
    try:
        resp = EMQXRequest().request_get(url)
        return resp.json()
    except Exception:
        return None


def get_resource(resource_name):
    url = f"{EMQXRequest.EMQX_API_URL}/sources/mqtt%3A{resource_name}"
    try:
        resp = EMQXRequest().request_get(url)
        return resp.json()
    except Exception:
        return None


def delete_all_by_rule(rule_id):
    rule_data = get_rule(rule_id)
    actions = rule_data.get("actions", [])
    sources = rule_data.get("from", [])
    delete_rule_mqtt(rule_id)

    if sources[0].startswith("$bridges/mqtt:"):
        try:
            resource_data = get_resource(sources[0].split("$bridges/mqtt:")[1])
            connector_name = resource_data.get("connector")
        except Exception:
            connector_name = None

        delete_resource_mqtt(sources[0].split("$bridges/mqtt:")[1])
        if connector_name:
            delete_connector_mqtt(connector_name)

    if actions[0].startswith("http:"):
        action_name = actions[0].split("http:")[1]
        delete_action_http(action_name)
    return True

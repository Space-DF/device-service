from django.conf import settings

from emqx.requests import EMQXRequest


def create_connector_http(name):
    url = f"{EMQXRequest.EMQX_API_URL}/connectors"
    payload = {
        "connect_timeout": "15s",
        "description": "",
        "enable_pipelining": 100,
        "headers": {"content-type": "application/json"},
        "name": name,
        "pool_size": 8,
        "pool_type": "random",
        "resource_opts": {"health_check_interval": "15s", "start_timeout": "5s"},
        "ssl": {"enable": True, "verify": "verify_none"},
        "type": "http",
        "url": settings.HOST,
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


def create_action_http(slug_name):
    url = f"{EMQXRequest.EMQX_API_URL}/actions"
    payload = {
        "connector": "connector_http_default",
        "enable": True,
        "name": f"action_{slug_name}_default",
        "parameters": {
            "body": '{\n  "payload": ${payload}\n}',
            "path": "api/receive-data",
            "method": "post",
            "headers": {"organization": slug_name},
        },
        "resource_opts": {
            "worker_pool_size": 16,
            "health_check_interval": "15s",
            "query_mode": "async",
            "request_ttl": "45s",
        },
        "type": "http",
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


def delete_connector_http(connector_id):
    url = f"{EMQXRequest.EMQX_API_URL}/connectors/http%3A{connector_id}"
    try:
        EMQXRequest().request_delete(
            url,
            headers={"Content-Type": "application/json"},
        )
        return True
    except Exception:
        return None


def delete_action_http(resource_id):
    url = f"{EMQXRequest.EMQX_API_URL}/actions/http%3A{resource_id}"
    try:
        EMQXRequest().request_delete(
            url,
            headers={"Content-Type": "application/json"},
        )
        return True
    except Exception:
        return None

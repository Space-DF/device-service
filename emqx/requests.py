import requests
from django.conf import settings


class EMQXRequest:
    _instance = None
    _token = None
    _token_expiry = None

    EMQX_API_URL = settings.EMQX_HOST

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EMQXRequest, cls).__new__(cls)
        return cls._instance

    def _get_token(self):
        url = f"{self.EMQX_API_URL}/login"
        payload = {"username": settings.USERNAME, "password": settings.PASSWORD}
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            token = response.json().get("token")
            if token:
                self._token = token
                return token
        raise Exception(f"Failed to get token: {response.text}")

    def _get_valid_token(self, force_refresh=False):
        if self._token is None or force_refresh:
            return self._get_token()
        return self._token

    def _authorized_request(self, method, url, headers=None, **kwargs):
        headers = headers.copy() if headers else {}
        token = self._get_valid_token()
        headers["Authorization"] = f"Bearer {token}"

        response = requests.request(method, url, headers=headers, timeout=5, **kwargs)

        if response.status_code == 401:
            token = self._get_valid_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            response = requests.request(
                method, url, headers=headers, timeout=5, **kwargs
            )

        if response.status_code in [200, 201, 204]:
            return response

        raise Exception(f"Failed to {method.upper()} data: {response.text}")

    def request_get(self, url, headers=None, params=None):
        return self._authorized_request("get", url, headers=headers, params=params)

    def request_post(self, url, headers=None, data=None):
        return self._authorized_request("post", url, headers=headers, json=data)

    def request_put(self, url, headers=None, data=None):
        return self._authorized_request("put", url, headers=headers, json=data)

    def request_delete(self, url, headers=None):
        return self._authorized_request("delete", url, headers=headers)

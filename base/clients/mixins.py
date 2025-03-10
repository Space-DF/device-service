from api import BaseClient


class BaseListMixin(BaseClient):
    def list(self, params: dict = {}):
        return self.make_request("GET", params=params)


class BaseRetrieveMixin(BaseClient):
    def retrieve(self, id: str, params: dict = {}):
        endpoint = f"{self.endpoint}/{id}"
        return self.make_request("GET", params=params, endpoint=endpoint)


class BaseCreateMixin(BaseClient):
    def create(self, data: dict):
        return self.make_request("POST", data=data)


class BaseUpdateMixin(BaseClient):
    def update(self, id: str, data: dict):
        endpoint = f"{self.endpoint}/{id}"
        return self.make_request("PUT", data=data, endpoint=endpoint)


class BaseDestroyMixin(BaseClient):
    def destroy(self, id: str):
        endpoint = f"{self.endpoint}/{id}"
        return self.make_request("DELETE", endpoint=endpoint)


__all__ = [
    "BaseListMixin",
    "BaseRetrieveMixin",
    "BaseCreateMixin",
    "BaseUpdateMixin",
    "BaseDestroyMixin",
]

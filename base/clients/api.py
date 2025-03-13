from abc import ABC, abstractmethod

from auth import BaseAuthenticator
from requests import request


class BaseClient(ABC):
    @property
    @abstractmethod
    def BASE_URL(self):
        """Subclasses must override BASE_URL."""
        pass

    def __init__(
        self, authenticator: BaseAuthenticator, endpoint: str, headers: dict = None
    ):
        self.authenticator = authenticator
        self.headers = headers or {}
        self.headers.update(self.authenticator.headers())
        self.endpoint = endpoint

    def make_request(
        self,
        method: str,
        params: dict = None,
        data: dict = None,
        endpoint: str = None,
        **kwargs,
    ):
        endpoint = endpoint if endpoint is not None else self.endpoint
        url = f"{self.BASE_URL}/{endpoint}"

        return request(
            method, url, headers=self.headers, params=params, json=data, **kwargs
        )


__all__ = ["BaseClient"]

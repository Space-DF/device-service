from abc import ABC, abstractmethod


class BaseAuthenticator(ABC):
    def __init__(self, token: str):
        self.token = token

    @property
    @abstractmethod
    def headers(self) -> dict:
        pass


class BearerAuthenticator(BaseAuthenticator):
    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


__all__ = ['BaseAuthenticator', 'BearerAuthenticator']

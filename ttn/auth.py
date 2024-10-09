from base.clients.auth import BaseAuthenticator, BearerAuthenticator


class TenantAdminKeyAuthenticator(BaseAuthenticator):
    @property
    def headers(self) -> dict:
        return {"Authorization": f"TenantAdminKey {self.token}"}


__all__ = ["BaseAuthenticator", "BearerAuthenticator", "TenantAdminKeyAuthenticator"]

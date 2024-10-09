from ..auth import TenantAdminKeyAuthenticator
from ..mixins import CRUDMixin


class TenantRegistry(CRUDMixin):
    def __init__(self, authenticator: TenantAdminKeyAuthenticator):
        super().__init__(authenticator, endpoint="tenants")

    def retrieve_registry_totals(self, tenant_id: str):
        endpoint = f"{self.endpoint}/{tenant_id}/registry-totals"
        return self.make_request("GET", endpoint=endpoint)

    def create_batch_get_registry_totals(self, data: dict):
        endpoint = f"{self.endpoint}/registry-totals"
        return self.make_request("POST", data=data, endpoint=endpoint)

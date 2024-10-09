"""
# These requests support a field_mask field for selecting fields to operate on.
By default, these API requests will not return or update most fields,unless they are specified in a field mask.
# The following fields are always returned:
    *Fields containing id
    *created_at
    *updated_at
    *deleted_at
# All other fields are not returned and not updated, unless specified.
Fields that are empty or zero are not returned, even if they are specified in a field mask.
More detail in here: https://www.thethingsindustries.com/docs/api/concepts/fieldmasks/
"""

from api import APIClient

from base.clients.mixins import (
    BaseCreateMixin,
    BaseDestroyMixin,
    BaseListMixin,
    BaseRetrieveMixin,
    BaseUpdateMixin,
)


class ListMixin(APIClient, BaseListMixin):
    def list(self, params: dict = {}, field_mask: list = []):
        if field_mask:
            params.update({"field_mask": ",".join(field_mask)})
        return super().list(params)


class RetrieveMixin(APIClient, BaseRetrieveMixin):
    def retrieve(self, id: str, params: dict = {}, field_mask: list = []):
        if field_mask:
            params.update({"field_mask": ",".join(field_mask)})
        return super().retrieve(id, params)


class CreateMixin(APIClient, BaseCreateMixin):
    pass


class UpdateMixin(APIClient, BaseUpdateMixin):
    def update(self, id: str, data: dict, field_mask: list = []):
        if field_mask:
            data["field_mask"] = {"paths": field_mask}
        return super().update(id, data)


class DestroyMixin(APIClient, BaseDestroyMixin):
    pass


class CRUDMixin(ListMixin, RetrieveMixin, CreateMixin, UpdateMixin, DestroyMixin):
    pass

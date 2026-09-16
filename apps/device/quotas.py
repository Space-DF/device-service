from contextlib import nullcontext

from common.apps.billing.constants import FeatureCode, FeatureUsageScope
from common.apps.billing.mixins import BaseQuota
from django.db.utils import DatabaseError
from django_tenants.utils import schema_context


class DeviceQuota(BaseQuota):
    reserve_actions = {"create", "bulk_create"}
    release_actions = {"destroy"}
    rules = {
        "create": {
            "feature": FeatureCode.DEVICE_MAX_COUNT,
            "scope": FeatureUsageScope.ORGANIZATION,
        },
        "bulk_create": {
            "feature": FeatureCode.DEVICE_MAX_COUNT,
            "scope": FeatureUsageScope.ORGANIZATION,
        },
        "destroy": {
            "feature": FeatureCode.DEVICE_MAX_COUNT,
            "scope": FeatureUsageScope.ORGANIZATION,
        },
    }

    def get_amount(self, request, view):
        if self.get_action(request, view) == "bulk_create" and isinstance(
            getattr(request, "data", None),
            list,
        ):
            organization = request.headers.get("X-Organization")
            try:
                with schema_context(organization) if organization else nullcontext():
                    serializer = view.get_serializer(
                        data=request.data,
                        many=True,
                        context=view.get_serializer_context(),
                    )
                    serializer.is_valid(raise_exception=False)
            except DatabaseError:
                return len(request.data)
            return len(getattr(serializer, "validated_data", []))
        return super().get_amount(request, view)

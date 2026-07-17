from common.apps.billing.constants import FeatureCode, FeatureUsageScope
from common.apps.billing.mixins import BaseQuota


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
            return len(request.data)
        return super().get_amount(request, view)

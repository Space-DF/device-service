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

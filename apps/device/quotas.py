from common.apps.billing.mixins import BaseQuota


class DeviceQuota(BaseQuota):
    reserve_actions = {"create", "bulk_create"}
    release_actions = {"destroy"}
    rules = {
        "create": "device.max_count",
        "bulk_create": "device.max_count",
        "destroy": "device.max_count",
    }

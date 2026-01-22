from apps.device_model.constants import KeyFeature
from apps.device_model.models import DeviceModel

default_device_models = [
    {
        "name": "lorawan",
        "device_type": "RAK2270",
        "key_feature": KeyFeature.LOCATION_TYPE,
    },
    {
        "name": "lorawan",
        "device_type": "RAK4630",
        "key_feature": KeyFeature.LOCATION_TYPE,
    },
    {
        "name": "lorawan",
        "device_type": "WLBV1",
        "key_feature": KeyFeature.WATER_DEPTH_TYPE,
    },
    {
        "name": "lorawan",
        "device_type": "SENSECAP_T1000",
        "key_feature": KeyFeature.LOCATION_TYPE,
    },
    {
        "name": "lorawan",
        "device_type": "ABEEWAY_INDUSTRIAL_TRACKER",
        "key_feature": KeyFeature.LOCATION_TYPE,
    },
]


def create_default_device_models():
    list_data = [
        DeviceModel(
            name=default_device_model.get("name"),
            device_type=default_device_model.get("device_type"),
            key_feature=default_device_model.get("key_feature"),
        )
        for default_device_model in default_device_models
    ]
    DeviceModel.objects.bulk_create(list_data)

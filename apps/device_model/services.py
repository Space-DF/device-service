from apps.device_model.models import DeviceModel

default_device_models = [
    {
        "name": "lorawan",
        "device_type": "RAK2270",
    },
    {
        "name": "lorawan",
        "device_type": "RAK4630",
    },
    {
        "name": "lorawan",
        "device_type": "WLBV1",
    },
    {
        "name": "lorawan",
        "device_type": "SENSECAP_T1000",
    },
    {
        "name": "lorawan",
        "device_type": "ABEEWAY_INDUSTRIAL_TRACKER",
    },
]


def create_default_device_models():
    list_data = [
        DeviceModel(
            name=default_device_model.get("name"),
            device_type=default_device_model.get("device_type"),
        )
        for default_device_model in default_device_models
    ]
    DeviceModel.objects.bulk_create(list_data)

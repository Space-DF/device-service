from apps.device_model.models import DeviceModel

default_device_models = [
    {
        "name": "lorawan",
        "device_type": "RAK Sticker",
    },
    {
        "name": "lorawan",
        "device_type": "RAK 4630",
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

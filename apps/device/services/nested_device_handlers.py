class NestedDeviceHandler:
    relation = None
    serializer_class = None
    model_class = None
    label = None
    identifier_field = None

    def pop_data(self, validated_data):
        return validated_data.pop(self.relation, None)

    def raw_data(self, item):
        return item.get(self.relation) or {}

    def get_identifier(self, item):
        if not self.identifier_field:
            return None
        return self.raw_data(item).get(self.identifier_field)

    def get_existing_identifiers(self, values):
        if not self.identifier_field:
            return set()
        return set(
            self.model_class.objects.filter(
                **{f"{self.identifier_field}__in": values}
            ).values_list(self.identifier_field, flat=True)
        )

    def build_instance(self, device, data):
        return self.model_class(device=device, **data)

    def create(self, device, data):
        if data:
            self.model_class.objects.create(device=device, **data)

    def update(self, device, data):
        if not data:
            return None

        nested_instance = getattr(device, self.relation, None)
        if nested_instance:
            serializer = self.serializer_class(
                instance=nested_instance,
                data=data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return "updated"

        self.create(device, data)
        return "created"


class LorawanDeviceHandler(NestedDeviceHandler):
    relation = "lorawan_device"
    label = "LoRaWAN device"
    identifier_field = "dev_eui"

    def __init__(self, serializer_class, model_class):
        self.serializer_class = serializer_class
        self.model_class = model_class


class APIDeviceHandler(NestedDeviceHandler):
    relation = "api_device"
    label = "API device"
    identifier_field = "serial_number"

    def __init__(self, serializer_class, model_class):
        self.serializer_class = serializer_class
        self.model_class = model_class


def get_nested_device_handlers():
    from apps.device.models import APIDevice, LorawanDevice
    from apps.device.serializers import APIDeviceSerializer, LorawanDeviceSerializer

    return [
        LorawanDeviceHandler(LorawanDeviceSerializer, LorawanDevice),
        APIDeviceHandler(APIDeviceSerializer, APIDevice),
    ]

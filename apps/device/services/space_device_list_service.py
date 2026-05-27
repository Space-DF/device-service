from apps.device.models import Device


class SpaceDeviceListService:
    ALLOWED_ORDERING_FIELDS = {"created_at", "name"}

    def __init__(self, request):
        self.request = request

    def get_public_devices_queryset(self):
        public_filters = {
            "is_published": True,
            "space_devices__isnull": True,
        }

        device_id = self.request.query_params.get("device_id")
        if device_id:
            public_filters["id"] = device_id

        public_devices = Device.objects.select_related("lorawan_device").filter(
            **public_filters
        )

        search = self.request.query_params.get("search")
        if search:
            public_devices = public_devices.filter(
                lorawan_device__dev_eui__icontains=search
            )

        return public_devices.distinct()

    def sort_results(self, results):
        ordering = self.request.query_params.get("ordering", "-created_at")
        field = ordering.lstrip("-")
        if field not in self.ALLOWED_ORDERING_FIELDS:
            field = "created_at"

        def sort_key(obj):
            value = getattr(obj, field, None)
            if field != "name" or value:
                return value

            lorawan_device = getattr(obj, "lorawan_device", None)
            return getattr(lorawan_device, "dev_eui", None) or str(obj.id)

        results.sort(key=sort_key, reverse=ordering.startswith("-"))
        return results

    def get_combined_results(self, space_devices):
        return self.sort_results(
            [
                *space_devices,
                *self.get_public_devices_queryset(),
            ]
        )

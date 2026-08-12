import django_filters
from django.db.models import Q

from apps.device.models import SpaceDevice
from apps.device.services.device_profile_resolver import resolve_device_type_filter


class SpaceDeviceFilter(django_filters.FilterSet):
    bbox = django_filters.CharFilter(method="filter_bbox")
    device_type = django_filters.CharFilter(method="filter_device_type")
    location = django_filters.BooleanFilter(method="filter_location")

    class Meta:
        model = SpaceDevice
        fields = [
            "bbox",
            "device_type",
            "location",
            "device_id",
            "building_id",
            "floor_id",
            "area_id",
            "facility_id",
        ]

    def filter_bbox(self, queryset, name, value):
        try:
            west, south, east, north = map(float, value.split(","))
        except ValueError:
            raise django_filters.exceptions.ValidationError(
                "Invalid bbox format. Expected format: west,south,east,north"
            )

        return queryset.filter(
            Q(device__location__isnull=False),
            Q(device__location__longitude__gte=west),
            Q(device__location__longitude__lte=east),
            Q(device__location__latitude__gte=south),
            Q(device__location__latitude__lte=north),
        )

    def filter_device_type(self, queryset, name, value):
        model_ids = resolve_device_type_filter(value)
        if model_ids is None:
            return queryset
        if not model_ids:
            return queryset.none()
        return queryset.filter(device__device_model__in=model_ids)

    def filter_location(self, queryset, name, value):
        return queryset.filter(device__location__isnull=not value)

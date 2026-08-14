import django_filters
from django.db.models import Q

from apps.device.models import Device, SpaceDevice
from apps.device.services.device_profile_resolver import resolve_key_feature_filter


class DeviceFilter(django_filters.FilterSet):
    location = django_filters.BooleanFilter(method="filter_location")
    key_feature = django_filters.CharFilter(method="filter_key_feature")

    class Meta:
        model = Device
        fields = [
            "status",
            "location",
            "key_feature",
            "is_published",
        ]

    def filter_location(self, queryset, name, value):
        return queryset.filter(location__isnull=not value)

    def filter_key_feature(self, queryset, name, value):
        model_ids = resolve_key_feature_filter(value)
        if model_ids is None:
            return queryset
        if not model_ids:
            return queryset.none()
        return queryset.filter(device_model__in=model_ids)


class SpaceDeviceFilter(django_filters.FilterSet):
    bbox = django_filters.CharFilter(method="filter_bbox")

    class Meta:
        model = SpaceDevice
        fields = [
            "bbox",
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

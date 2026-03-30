import django_filters
from django.db.models import Q

from apps.device.models import SpaceDevice


class SpaceDeviceFilter(django_filters.FilterSet):
    bbox = django_filters.CharFilter(method="filter_bbox")
    device_id = django_filters.UUIDFilter(field_name="device__id")

    class Meta:
        model = SpaceDevice
        fields = ["bbox", "device_id"]

    def filter_bbox(self, queryset, name, value):
        try:
            west, south, east, north = map(float, value.split(","))
        except ValueError:
            raise django_filters.exceptions.ValidationError(
                "Invalid bbox format. Expected format: west,south,east,north"
            )

        return queryset.filter(
            Q(location__isnull=False),
            Q(location__longitude__gte=west),
            Q(location__longitude__lte=east),
            Q(location__latitude__gte=south),
            Q(location__latitude__lte=north),
        )

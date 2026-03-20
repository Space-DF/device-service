import django_filters
from django.contrib.gis.geos import Polygon

from apps.device.models import SpaceDevice


class SpaceDeviceFilter(django_filters.FilterSet):
    bbox = django_filters.CharFilter(method="filter_bbox")

    class Meta:
        model = SpaceDevice
        fields = ["bbox"]

    def filter_bbox(self, queryset, name, value):
        try:
            west, south, east, north = map(float, value.split(","))
        except ValueError:
            raise django_filters.exceptions.ValidationError(
                "Invalid bbox format. Expected format: west,south,east,north"
            )

        bounding_box = Polygon(
            [(west, south), (west, north), (east, north), (east, south), (west, south)]
        )
        return queryset.filter(location__within=bounding_box)

from common.pagination.base_pagination import BasePagination
from common.views.space import SpaceListCreateAPIView, SpaceRetrieveUpdateDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.facility.models import Facility
from apps.facility.serializers import FacilitySerializer


class FacilityListCreateView(SpaceListCreateAPIView):
    queryset = Facility.objects.select_related("space").all()
    serializer_class = FacilitySerializer
    pagination_class = BasePagination
    filter_backends = [DjangoFilterBackend]
    search_fields = ["name"]
    space_field = "space"


class FacilityRetrieveUpdateDestroyView(SpaceRetrieveUpdateDestroyAPIView):
    queryset = Facility.objects.select_related("space").all()
    serializer_class = FacilitySerializer
    space_field = "space"

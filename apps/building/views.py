from common.pagination.base_pagination import BasePagination
from common.views.space import SpaceListCreateAPIView, SpaceRetrieveUpdateDestroyAPIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from apps.building.models import Area, Building, Floor
from apps.building.serializers import (
    AreaSerializer,
    BuildingSerializer,
    FloorSerializer,
)


class BuildingListCreateView(SpaceListCreateAPIView):
    queryset = Building.objects.select_related("space").all()
    serializer_class = BuildingSerializer
    pagination_class = BasePagination
    space_field = "space"
    filter_backends = [DjangoFilterBackend]
    search_fields = ["name"]


class BuildingRetrieveUpdateDestroyView(SpaceRetrieveUpdateDestroyAPIView):
    queryset = Building.objects.select_related("space").all()
    space_field = "space"
    serializer_class = BuildingSerializer


class FloorListCreateView(SpaceListCreateAPIView):
    queryset = Floor.objects.select_related("building").all()
    space_field = "building__space"
    serializer_class = FloorSerializer
    pagination_class = BasePagination
    filter_backends = [DjangoFilterBackend]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset()
        return super().get_queryset().filter(building_id=self.kwargs["building_id"])

    def perform_create(self, serializer):
        building = get_object_or_404(Building, pk=self.kwargs["building_id"])
        serializer.save(building=building)


class FloorRetrieveUpdateDestroyView(SpaceRetrieveUpdateDestroyAPIView):
    queryset = Floor.objects.select_related("building").all()
    serializer_class = FloorSerializer
    space_field = "building__space"
    lookup_url_kwarg = "floor_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset()
        return super().get_queryset().filter(building_id=self.kwargs["building_id"])


class AreaListCreateView(SpaceListCreateAPIView):
    queryset = Area.objects.select_related("floor", "floor__building").all()
    serializer_class = AreaSerializer
    space_field = "floor__building__space"
    pagination_class = BasePagination
    filter_backends = [DjangoFilterBackend]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset()
        return (
            super()
            .get_queryset()
            .filter(
                floor_id=self.kwargs["floor_id"],
            )
        )

    def perform_create(self, serializer):
        floor = get_object_or_404(Floor, pk=self.kwargs["floor_id"])
        serializer.save(floor=floor)


class AreaRetrieveUpdateDestroyView(SpaceRetrieveUpdateDestroyAPIView):
    queryset = Area.objects.select_related("floor", "floor__building").all()
    serializer_class = AreaSerializer
    space_field = "floor__building__space"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_queryset()
        return super().get_queryset().filter(floor_id=self.kwargs["floor_id"])

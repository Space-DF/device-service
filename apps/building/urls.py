from django.urls import path

from apps.building.views import (
    AreaListCreateView,
    AreaRetrieveUpdateDestroyView,
    BuildingListCreateView,
    BuildingRetrieveUpdateDestroyView,
    FloorListCreateView,
    FloorRetrieveUpdateDestroyView,
)

app_name = "building"

urlpatterns = [
    path(
        "floors/<uuid:floor_id>/areas",
        AreaListCreateView.as_view(),
        name="area-list-create",
    ),
    path(
        "floors/<uuid:floor_id>/areas/<uuid:pk>",
        AreaRetrieveUpdateDestroyView.as_view(),
        name="area-detail",
    ),
    path(
        "buildings/<uuid:building_id>/floors",
        FloorListCreateView.as_view(),
        name="floor-list-create",
    ),
    path(
        "buildings/<uuid:building_id>/floors/<uuid:floor_id>",
        FloorRetrieveUpdateDestroyView.as_view(),
        name="floor-detail",
    ),
    path("buildings", BuildingListCreateView.as_view(), name="building-list-create"),
    path(
        "buildings/<uuid:pk>",
        BuildingRetrieveUpdateDestroyView.as_view(),
        name="building-detail",
    ),
]

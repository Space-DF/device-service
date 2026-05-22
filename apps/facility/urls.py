from django.urls import path

from apps.facility.views import (
    FacilityListCreateView,
    FacilityRetrieveUpdateDestroyView,
)

app_name = "facility"

urlpatterns = [
    path("facilities/", FacilityListCreateView.as_view(), name="facility-list-create"),
    path(
        "facilities/<uuid:pk>/",
        FacilityRetrieveUpdateDestroyView.as_view(),
        name="facility-detail",
    ),
]

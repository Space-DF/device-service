"""device_service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from common.swagger.views import get_tenant_schema_view
from django.urls import include, path, re_path
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_tenant_schema_view(
    openapi.Info(
        title="SPACEDF DEVICE API",
        default_version="v1",
        terms_of_service="https://spacedf.com/terms-of-service",
        contact=openapi.Contact(email="hello@df.technology"),
        license=openapi.License(name="Apache 2.0"),
    ),
    path="/api/",
    public=True,
    permission_classes=[permissions.AllowAny],
)


urlpatterns = [
    # docs
    re_path(
        r"^device/docs/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    # apis
    path("api/", include("apps.network_server.urls", namespace="network_server")),
    path("api/", include("apps.device.urls", namespace="device")),
    path("api/", include("apps.building.urls", namespace="building")),
    path("api/", include("apps.facility.urls", namespace="facility")),
]

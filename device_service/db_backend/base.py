from django.contrib.gis.db.backends.postgis.base import (
    DatabaseWrapper as PostGISWrapper,
)
from django_tenants.postgresql_backend.base import DatabaseWrapper as TenantWrapper


class DatabaseWrapper(TenantWrapper, PostGISWrapper):
    ...

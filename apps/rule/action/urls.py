from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.rule.action.views import ActionViewSet

app_name = "rule.action"

router = DefaultRouter()
router.register("rule-actions", ActionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

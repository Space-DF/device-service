from common.pagination.base_pagination import BasePagination
from rest_framework import viewsets

from apps.device_model.views import UseTenantFromRequestMixin
from apps.rule.action.models import Action
from apps.rule.action.serializers import ActionSerializer


class ActionViewSet(UseTenantFromRequestMixin, viewsets.ModelViewSet):
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    pagination_class = BasePagination

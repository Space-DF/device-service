from rest_framework.serializers import ModelSerializer

from apps.rule.action.models import Action


class ActionSerializer(ModelSerializer):

    class Meta:
        model = Action
        fields = "__all__"

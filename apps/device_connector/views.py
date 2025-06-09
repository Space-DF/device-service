from abc import ABC, abstractmethod

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.device_connector.models import DeviceConnector, DeviceMqttConfig
from apps.device_connector.serializers import DeviceConnectorSerializer
from apps.device_connector.services import (
    create_connector_mqtt,
    create_resource_mqtt,
    create_rule_mqtt,
    delete_connector_mqtt,
    delete_resource_mqtt,
    delete_rule_mqtt,
    test_connect_mqtt,
)
from apps.device_model.views import UseTenantFromRequestMixin
from apps.rule.action.models import Action
from apps.rule.definition.models import Definition
from apps.rule.resource.models import Resource


class ConnectorStrategy(ABC):
    @abstractmethod
    def create_connector(self, data, slug_name):
        pass

    @abstractmethod
    def delete_connector(self, connector_id, slug_name):
        pass

    @abstractmethod
    def test_connector_preview(self, data):
        pass

    @abstractmethod
    def test_connector(self, connector_id, name):
        pass


class MqttConnectorStrategy(ConnectorStrategy):

    @transaction.atomic
    def create_connector(self, data, slug_name):
        mqtt_config = data.get("device_mqtt_config")
        if not mqtt_config:
            transaction.set_rollback(True)
            raise Exception("Failed to get mqtt_config")

        device_connector = DeviceConnector.objects.create(
            network_server=data.get("network_server"),
            name=data.get("name"),
            connector_type=data.get("connector_type"),
            status=data.get("status"),
        )

        DeviceMqttConfig.objects.create(
            device_connector=device_connector,
            username=mqtt_config.get("username"),
            password=mqtt_config.get("password"),
            mqtt_broker=mqtt_config.get("mqtt_broker"),
        )

        result_create_connector = create_connector_mqtt(data)
        if not result_create_connector:
            raise Exception("Failed to create connector")

        result_create_resource = create_resource_mqtt(data)
        if not result_create_resource:
            delete_connector_mqtt(data.get("name"))
            raise Exception("Failed to create resource")

        resource = Resource.objects.create(
            device_connector=device_connector,
            enable=result_create_resource.get("enable"),
            name=result_create_resource.get("name"),
            parameters=result_create_resource.get("parameters"),
            resource_opts=result_create_resource.get("resource_opts"),
            type=result_create_resource.get("type"),
        )
        action = Action.objects.filter(name=f"action_{slug_name}_default").first()
        result_create_rule = create_rule_mqtt(data, action)
        if not result_create_rule:
            delete_resource_mqtt(result_create_resource.get("name"))
            delete_connector_mqtt(data.get("name"))
            raise Exception("Failed to create rule")

        Definition.objects.create(
            resource=resource,
            rule_id=result_create_rule.get("id"),
            description=result_create_rule.get("description"),
            action=action,
            sql=result_create_rule.get("sql"),
        )

        return DeviceConnectorSerializer(device_connector).data

    def delete_connector(self, connector, slug_name):
        device_rule = Definition.objects.filter(
            resource__device_connector=connector
        ).first()
        device_resource = Resource.objects.filter(device_connector=connector).first()

        result_delete_rule = delete_rule_mqtt(device_rule.rule_id)
        if not result_delete_rule:
            raise Exception("Failed to delete MQTT rule")

        result_delete_resource = delete_resource_mqtt(device_resource.name)
        serializer = DeviceConnectorSerializer(connector)
        if not result_delete_resource:
            action = Action.objects.filter(name=f"action_{slug_name}_default").first()
            result = create_rule_mqtt(serializer.data, action)
            device_rule.rule_id = result.get("id")
            device_rule.save()
            raise Exception("Failed to delete MQTT resource")

        result_delete_connector = delete_connector_mqtt(connector.name)
        if not result_delete_connector:
            action = Action.objects.filter(name=f"action_{slug_name}_default").first()
            create_resource_mqtt(serializer.data)
            result = create_rule_mqtt(serializer.data, action)
            device_rule.rule_id = result.get("id")
            device_rule.save()
            raise Exception("Failed to delete MQTT connector")

        connector.delete()
        return True

    def test_connector_preview(self, data):
        mqtt_config = data.get("device_mqtt_config")
        return (
            test_connect_mqtt(
                data.get("name"),
                mqtt_config.get("mqtt_broker"),
                mqtt_config.get("username"),
                mqtt_config.get("password"),
            )
            is True
        )

    def test_connector(self, connector_id, name):
        device_mqtt_config = DeviceMqttConfig.objects.filter(
            device_connector_id=connector_id
        ).first()
        if device_mqtt_config:
            return (
                test_connect_mqtt(
                    name,
                    device_mqtt_config.mqtt_broker,
                    device_mqtt_config.username,
                    device_mqtt_config.password,
                )
                is True
            )
        return False


class HttpConnectorStrategy(ConnectorStrategy):
    def create_connector(self, data):
        # Implement HTTP connector creation logic
        return {"message": "HTTP Connector created", "data": data}

    def delete_connector(self, connector):
        pass

    def test_connector_preview(self, data):
        return False

    def test_connector(self, connector_id, name):
        pass


class ConnectorFactory:
    strategies = {
        "http_server": HttpConnectorStrategy,
        "mqtt_broker": MqttConnectorStrategy,
    }

    @classmethod
    def get_strategy(cls, connector_type):
        strategy = cls.strategies.get(connector_type)
        if not strategy:
            raise ValueError(f"Unknown connector type: {connector_type}")
        return strategy()


class APIDeviceConnectorView(
    UseTenantFromRequestMixin,
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.mixins.DestroyModelMixin,
):
    serializer_class = DeviceConnectorSerializer
    queryset = DeviceConnector.objects.all()
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ["network_server"]

    def create(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            connector_type = request.data.get("connector_type")
            connector = ConnectorFactory.get_strategy(connector_type)
            slug_name = request.tenant.slug_name
            response = connector.create_connector(serializer.validated_data, slug_name)
            if response is None:
                return Response(
                    {"error": "Failed to create connector."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(response, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            device_connector = DeviceConnector.objects.get(id=pk)
        except DeviceConnector.DoesNotExist:
            raise NotFound("DeviceConnector not found!")

        connector_factory = ConnectorFactory.get_strategy(
            device_connector.connector_type
        )
        slug_name = request.tenant.slug_name
        connector_factory.delete_connector(device_connector, slug_name)
        return Response(
            {"message": "Delete the connector successful"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["post"], url_path="test-connection-preview")
    def test_connector_preview(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            connector_type = request.data.get("connector_type")
            connector_factory = ConnectorFactory.get_strategy(connector_type)
            response = connector_factory.test_connector_preview(
                serializer.validated_data
            )
            if response:
                return Response(
                    {"message": "Connection successful."},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"message": "Connection failed!"}, status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="test-connection")
    def test_connector_by_id(self, request, pk=None):
        try:
            connector = DeviceConnector.objects.get(id=pk)
            connector_factory = ConnectorFactory.get_strategy(connector.connector_type)
            response = connector_factory.test_connector(pk, connector.name)
            if response:
                return Response(
                    {"message": "Connection successful."},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"message": "Connection failed!"}, status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

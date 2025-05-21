from abc import ABC, abstractmethod

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.device_connector.models import DeviceConnector, DeviceMqttConfig
from apps.device_connector.serializers import DeviceConnectorSerializer
from apps.device_connector.services import test_connect_mqtt


class ConnectorStrategy(ABC):
    @abstractmethod
    def create_connector(self, data):
        pass

    @abstractmethod
    def get_connector(self, connector_id):
        pass

    @abstractmethod
    def test_connector_preview(self, data):
        pass

    @abstractmethod
    def test_connector(self, connector_id, name):
        pass


class MqttConnectorStrategy(ConnectorStrategy):
    def create_connector(self, data):
        # Implement MQTT connector creation logic
        return {"message": "MQTT Connector created", "data": data}

    def get_connector(self, connector_id):
        # Implement MQTT connector retrieval logic
        return {"message": "MQTT Connector retrieved", "id": connector_id}

    def test_connector_preview(self, data):
        mqtt_config = data.get("deviceMqttConfig")
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
                    device_mqtt_config.get("mqtt_broker"),
                    device_mqtt_config.get("username"),
                    device_mqtt_config.get("password"),
                )
                is True
            )
        return False


class HttpConnectorStrategy(ConnectorStrategy):
    def create_connector(self, data):
        # Implement HTTP connector creation logic
        return {"message": "HTTP Connector created", "data": data}

    def get_connector(self, connector_id):
        # Implement HTTP connector retrieval logic
        return {"message": "HTTP Connector retrieved", "id": connector_id}

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


class APIApplicationView(viewsets.GenericViewSet):
    serializer_class = DeviceConnectorSerializer
    queryset = DeviceConnector.objects.all()

    def create(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            connector_type = request.data.get("connector_type")
            connector = ConnectorFactory.get_strategy(connector_type)
            response = connector.create_connector(serializer.validated_data)
            return Response(response, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=False, methods=["get"], url_path="test-connection/{id}")
    def test_connector_by_id(self, request):
        try:
            connector_id = request.query_params.get("id")
            connector = DeviceConnector.objects.get(id=connector_id)
            connector_factory = ConnectorFactory.get_strategy(connector.connector_type)
            response = connector_factory.test_connector(connector_id, connector.name)
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

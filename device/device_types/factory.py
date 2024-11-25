from rest_framework.exceptions import ValidationError

from device_model.models import DeviceType

from .chirpstack.strategy import ChirpstackDeviceTypeStrategy
from .mqtt.strategy import MqttDeviceTypeStrategy
from .ttn.strategy import TnnDeviceTypeStrategy
from .ttn_gateway.strategy import TnnGatewayTypeStrategy

DEVICE_TYPE_STRATEGIES = {
    DeviceType.Chirpstack: ChirpstackDeviceTypeStrategy,
    DeviceType.TTN: TnnDeviceTypeStrategy,
    DeviceType.TTN_GATEWAY: TnnGatewayTypeStrategy,
    DeviceType.MQTT: MqttDeviceTypeStrategy,
}


class DeviceTypeStrategyFactory:
    @staticmethod
    def get_strategy(device_type: DeviceType):
        strategy_class = DEVICE_TYPE_STRATEGIES.get(device_type)
        if not strategy_class:
            raise ValidationError(f"Invalid device_type: {device_type}")
        return strategy_class

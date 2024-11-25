from abc import ABC, abstractmethod


class BaseDeviceTypeStrategy(ABC):
    @property
    @abstractmethod
    def component_related_names(self):
        pass

    @property
    @abstractmethod
    def serializer(self):
        pass

    @property
    @abstractmethod
    def read_serializer(self):
        pass

    def create_device(self, data: dict):
        serializer_instance = self.serializer(data=data)
        serializer_instance.is_valid(raise_exception=True)
        self.preform_create_device(serializer_instance)
        return serializer_instance

    def preform_create_device(self, serializer_instance):
        return serializer_instance.save()

from abc import ABC, abstractmethod


class BaseClient(ABC):
    @abstractmethod
    def predict(self, jpeg: bytes) -> str:
        """Return the raw action prediction for one observed frame."""
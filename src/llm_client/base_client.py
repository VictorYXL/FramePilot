from abc import ABC, abstractmethod


class BaseClient(ABC):
    def reset(self) -> None:
        """Forget episode history; stateless providers need no action."""

    @abstractmethod
    def predict(self, jpeg: bytes) -> str:
        """Return the raw action prediction for one observed frame."""
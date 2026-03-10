from abc import ABC, abstractmethod
from typing import Any, Dict
from config.logger import get_logger

class BaseAgent(ABC):
    def __init__(self, name: str, capabilities: list[str]):
        self.name = name
        self.capabilities = capabilities
        self.logger = get_logger(self.name.replace(" ", ""))

    @abstractmethod
    def run(self, prompt: str, context: Dict[str, Any] = None) -> Any:
        pass

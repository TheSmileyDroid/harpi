from abc import ABC, abstractmethod


class IMessageParser(ABC):
    @abstractmethod
    async def send(self, content: str) -> None:
        pass

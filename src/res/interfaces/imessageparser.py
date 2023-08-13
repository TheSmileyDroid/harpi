from abc import ABCMeta, abstractmethod


class IMessageParser(metaclass=ABCMeta):
    @abstractmethod
    async def send(self, content: str) -> None:
        pass

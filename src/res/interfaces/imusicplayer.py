from abc import ABCMeta, abstractmethod


from .imusicdata import IMusicData

from .imusicqueue import IMusicQueue


class IMusicPlayer(metaclass=ABCMeta):
    @abstractmethod
    async def play(self, text: str):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def pause(self):
        pass

    @abstractmethod
    async def resume(self):
        pass

    @abstractmethod
    async def skip(self):
        pass

    @abstractmethod
    async def queue(self) -> IMusicQueue:
        pass

    @abstractmethod
    async def remove(self, index: int) -> None:
        pass

    @abstractmethod
    async def set_loop(self, loop: bool) -> None:
        pass

    @abstractmethod
    async def set_volume(self, volume: float) -> None:
        pass

    @abstractmethod
    async def get_volume(self) -> float:
        pass

    @abstractmethod
    async def get_current(self) -> IMusicData:
        pass

    @abstractmethod
    async def shuffle(self) -> None:
        pass

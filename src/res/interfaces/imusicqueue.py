from abc import ABC, abstractmethod
from typing import Iterator

from .imusicdata import IMusicData


class IMusicQueue(ABC):
    @abstractmethod
    def add(self, song: IMusicData) -> None:
        pass

    @abstractmethod
    def get(self, index: int) -> IMusicData:
        pass

    @abstractmethod
    def get_by_title(self, title: str) -> IMusicData:
        pass

    @abstractmethod
    def get_by_url(self, url: str) -> IMusicData:
        pass

    @abstractmethod
    def remove(self, song: IMusicData) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def shuffle(self) -> None:
        pass

    @abstractmethod
    def get_length(self) -> int:
        pass

    @abstractmethod
    def get_current(self) -> IMusicData:
        pass

    @abstractmethod
    def get_next(self) -> IMusicData:
        pass

    @abstractmethod
    def remove_current(self) -> None:
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[IMusicData]:
        pass

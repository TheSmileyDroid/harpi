from abc import ABC, abstractmethod

import discord


class IMusicData(ABC):
    @classmethod
    @abstractmethod
    def from_url(cls, url: str) -> None:
        pass

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_artist(self) -> str:
        pass

    @abstractmethod
    def get_url(self) -> str:
        pass

    @abstractmethod
    async def get_source(self) -> discord.AudioSource:
        pass

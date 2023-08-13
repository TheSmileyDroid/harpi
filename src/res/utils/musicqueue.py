from typing import Iterator
from ..interfaces.imusicdata import IMusicData
from ..interfaces.imusicqueue import IMusicQueue

import random


class MusicQueue(IMusicQueue):
    def __init__(self) -> None:
        self._queue: list[IMusicData] = []

    def add(self, song: IMusicData) -> None:
        self._queue.append(song)

    def get(self, index: int) -> IMusicData:
        return self._queue[index]

    def get_by_title(self, title: str) -> IMusicData:
        for song in self._queue:
            if song.get_title() == title:
                return song

        raise ValueError(f"Música com o titúlo {title} não encontrado")

    def get_by_url(self, url: str) -> IMusicData:
        for song in self._queue:
            if song.get_url() == url:
                return song

        raise ValueError(f"Música com a url {url} não encontrado")

    def remove(self, song: IMusicData) -> None:
        for index, item in enumerate(self._queue):
            if item == song:
                self._queue.pop(index)
                return

    def clear(self) -> None:
        self._queue.clear()

    def shuffle(self) -> None:
        random.shuffle(self._queue)

    def get_length(self) -> int:
        return len(self._queue)

    def get_current(self) -> IMusicData:
        return self._queue[0]

    def get_next(self) -> IMusicData:
        return self._queue[1]

    def remove_current(self) -> None:
        self._queue.pop(0)

    def __iter__(self) -> Iterator[IMusicData]:
        return iter(self._queue)

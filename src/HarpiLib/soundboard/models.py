from dataclasses import dataclass, field


@dataclass
class Node:
    x: int
    y: int
    sound_uuid: str
    volume: int


@dataclass
class Soundboard:
    nodes: list[Node] = field(default_factory=list)

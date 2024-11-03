"""Docstring for src.HarpiLib.dice.dice_component."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class DiceComponent:
    """Represents a dice component. With the info count, sides and modifier.

    Examples
    --------
    >>> DiceComponent(
    ...     2, 6, 0
    ... )
    DiceComponent(count=2, sides=6, modifier=0)

    """

    count: int
    sides: int
    modifier: int = 0

    def roll(self) -> tuple[list[int], int]:
        """Roll the dice and get the results.

        Returns:
            tuple[list[int], int]: A list with the rolls and the result.

        """
        rolls = [random.randint(1, self.sides) for _ in range(self.count)]  # noqa: S311
        return rolls, sum(rolls) + self.modifier

    def __str__(self) -> str:
        """Get a string representation of the dice roll.

        Returns:
            str: A string representation of the dice roll.

        """
        if self.sides == 0:
            return str(self.modifier)
        return f"{self.count}d{self.sides}" + (
            f"+{self.modifier}" if self.modifier else ""
        )


if __name__ == "__main__":
    import doctest

    doctest.testmod()

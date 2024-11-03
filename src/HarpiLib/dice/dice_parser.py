"""Docstring for src.HarpiLib.dice.dice_parser."""

from __future__ import annotations

import re

from src.HarpiLib.dice.dice_component import DiceComponent


class DiceParser:
    """Parses a dice string into a list of DiceComponent objects."""

    def __init__(self, dice_string: str) -> None:
        """Initialize the DiceParser with a dice string.

        Parameters
        ----------
        dice_string : str
            The dice string to parse.

        Raises
        ------
        ValueError
            If the dice string is invalid.

        Examples
        --------
        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> len(
        ...     parser.component_register[
        ...         0
        ...     ]
        ... )
        1
        >>> parser = DiceParser(
        ...     "2d6+3+2d"
        ... )
        >>> len(
        ...     parser.component_register[
        ...         0
        ...     ]
        ... )
        3

        """
        self.dice_string = dice_string
        self.component_register: list[list[tuple[str, DiceComponent]]] = []
        if not self.is_valid_dice_string(self.dice_string):
            msg = "Invalid dice string"
            raise ValueError(msg)
        self._parse()

    @staticmethod
    def is_valid_dice_string(dice_string: str) -> bool:
        """Check if it is a valid dice string.

        Returns:
            bool: True if it is a valid dice string, False otherwise.

        Examples:
        --------
        >>> DiceParser.is_valid_dice_string(
        ...     "2d6"
        ... )
        True
        >>> DiceParser.is_valid_dice_string(
        ...     "2#d"
        ... )
        True

        """
        pattern = r"^([+-]?[#]?(\d*d\d*|\d+))+$"
        return re.match(pattern, dice_string.replace(" ", "")) is not None

    def _parse(self) -> None:
        """Parse the dice string and store the results in the `self.results` list.

        Examples
        --------
        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> len(
        ...     parser.component_register
        ... )
        1

        """  # noqa: E501
        components = []
        count_of_rows = 1
        if self.dice_string.count("#") >= 1:
            count_of_rows = int(self.dice_string.split("#")[0])

        _dice_tring = self.dice_string.split("#")[-1].replace(" ", "")

        for i in range(count_of_rows):
            components.append([])
            pattern = r"([+-]?)(\d*d?\d*)"
            matches = re.findall(
                pattern,
                _dice_tring,
            )

            for sign, value in matches:
                if len(value) == 0:
                    continue
                if "d" in value:
                    count, sides = (
                        int(x) if x else 1 for x in value.split("d")
                    )
                    if sides == 1:
                        sides = 20
                    components[i].append((sign, DiceComponent(count, sides)))
                else:
                    components[i].append((
                        sign,
                        DiceComponent(0, 0, int(value)),
                    ))
        self.component_register = components

    def roll(self) -> list[tuple[int, list[str]]]:
        """Roll the dice and return the total and the results.

        Returns:
            tuple[int, list[str]]: The total and the results.

        Examples:
        --------
        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> total, results = (
        ...     parser.roll()
        ... )[0]
        >>> len(results)
        1
        >>> total >= 2 and total <= 12
        True
        >>> parser = DiceParser(
        ...     "2#d+10"
        ... )
        >>> total, results = (
        ...     parser.roll()
        ... )[0]
        >>> len(results)
        2
        >>> total >= 1 and total <= 30
        True
        >>> total, results = (
        ...     parser.roll()
        ... )[1]
        >>> len(results)
        2
        >>> total >= 1 and total <= 30
        True
        >>> len(parser.roll())
        2

        """
        row_results = []

        for components in self.component_register:
            total = 0
            results: list[str] = []
            for sign, component in components:
                rolls, result = component.roll()
                if sign == "-":
                    total -= result
                else:
                    total += result
                if component.sides != 0:
                    results.append(
                        f"[{self._format_rolls(rolls, component.sides)}]",
                    )
                else:
                    results.append("")
            row_results.append((total, results))
        return row_results

    @staticmethod
    def _format_rolls(rolls: list[int], sides: int) -> str:
        """Format the rolls.

        Args:
            rolls (list[int]): The rolls.
            sides (int): The sides of the dice.

        Returns:
            str: The formatted rolls.

        """
        return ", ".join(
            f"**{roll}**" if roll == sides else str(roll) for roll in rolls
        )


if __name__ == "__main__":
    import doctest

    doctest.testmod()

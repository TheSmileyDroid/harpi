from abc import ABC, abstractmethod


class DiceRoller(ABC):
    @abstractmethod
    def roll(self, number_of_dice: int, number_of_sides: int) -> list[int]:
        """
        Rolls a number of dice with a number of sides and returns a list of the results.

        :param self DiceRoller
        :param number_of_dice 
        :param number_of_sides
        :return list[int]
        """
        pass

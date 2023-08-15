from abc import ABC, abstractmethod


class DiceResults:
    def __init__(self, dice: str, results: list[int], total: int):
        self.dice = dice
        self.results = results
        self.total = total


class IDiceHandler(ABC):
    @abstractmethod
    def froll(self, dice: str) -> DiceResults:
        """
        Roll the dices and return the result.
        :return: The result of all the rolls formated.
        """
        pass


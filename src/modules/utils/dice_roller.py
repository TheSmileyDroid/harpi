import random
import re
from abc import ABC, abstractmethod


class DiceRoller(ABC):
    @abstractmethod
    def roll(self, number_of_dice: int, number_of_sides: int) -> int:
        pass


class RandomDiceRoller(DiceRoller):
    def roll(self, number_of_dice: int, number_of_sides: int) -> int:
        random.seed()
        result = 0
        for _ in range(number_of_dice):
            result += random.randint(1, number_of_sides)
        return result


class DiceHandler:
    def __init__(self, dice_roller: DiceRoller = RandomDiceRoller()):
        self.dice_roller = dice_roller

    def froll(self, dice: str) -> str:
        result = self.parse(dice)
        return result

    def parse(self, dice: str) -> str:
        hashtag = dice.find("#")
        if hashtag != -1:
            count = int(dice[:hashtag])
            dice = dice[hashtag + 1:]
            result = ""
            for _ in range(count):
                result += f"{self.parse(dice)}\n"
            return result
        else:
            return self._parse_simple(dice)

    def _parse_simple(self, dice: str) -> str:
        # Split the dice string on the + and - operators
        parts = re.split(r'([+-])', dice)
        total = 0
        partial = ''
        op: int = 1
        for part in parts:
            if part == '+':
                op = 1
                partial += ' + '
            elif part == '-':
                op = -1
                partial += ' - '
            elif 'd' in part:
                # Parse the dice roll
                count, sides = part.split('d')
                partial_result = self.dice_roller.roll(
                    int(count), int(sides)) * op
                partial += f'{count}d{sides} [{partial_result}]'
                total += partial_result
            else:
                # Parse the constant value
                total += int(part) * op
                partial += f'{part}'
        # Return the total as a string
        return f'{total} = {partial}'

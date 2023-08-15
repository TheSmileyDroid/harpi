import random
import re
from typing import List
from ..interfaces.idiceroller import DiceRoller


class RandomDiceRoller(DiceRoller):
    def roll(self, number_of_dice: int, number_of_sides: int) -> list[int]:
        if number_of_dice < 1:
            raise ValueError("Número de dados deve ser maior que 0")
        if number_of_sides < 2:
            raise ValueError("Número de lados deve ser maior que 1")
        if number_of_dice > 100:
            raise ValueError("Número de dados deve ser menor que 100")
        if number_of_sides > 1000:
            raise ValueError("Número de lados deve ser menor que 1000")
        random.seed()
        result = []
        for _ in range(number_of_dice):
            result.append(random.randint(1, number_of_sides))
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
            is_negative = count < 0
            if is_negative:
                count = abs(count) + 1
            dice = dice[hashtag + 1 :]
            result_list: List[str] = []
            for _ in range(count):
                result_list.append(f"{self.parse(dice)}\n")
            if is_negative:
                return self.format_hashtag_result_negative(result_list)
            return self.format_hashtag_result_positive(result_list)
        else:
            return self._parse_simple(dice)

    def format_hashtag_result_positive(self, result_list: List[str]) -> str:
        result = ""
        max_value = max([int(x.split(" ")[0]) for x in result_list if x])
        for result_value in result_list:
            if result_value:
                if int(result_value.split(" ")[0]) == max_value:
                    result += f"__{result_value}__"
                else:
                    result += result_value
        return result

    def format_hashtag_result_negative(self, result_list: List[str]) -> str:
        result = ""
        min_value = min([int(x.split(" ")[0]) for x in result_list if x])
        for result_value in result_list:
            if result_value:
                if int(result_value.split(" ")[0]) == min_value:
                    result += f"__{result_value}__"
                else:
                    result += result_value
        return result

    def _parse_simple(self, dice: str) -> str:
        # Split the dice string on the + and - operators
        parts = re.split(r"([+-])", dice)
        total = 0
        partial = ""
        op: int = 1
        for part in parts:
            if part == "+":
                op = 1
                partial += " + "
            elif part == "-":
                op = -1
                partial += " - "
            elif "d" in part:
                # Parse the dice roll
                count, sides = part.split("d")
                partial_result = self.dice_roller.roll(int(count), int(sides)) * op
                partial += f"{count}d{sides} ["
                for i, value in enumerate(partial_result):
                    partial += (
                        f"**{value}**"
                        if value == int(sides) or value == 1
                        else f"{value}"
                    )
                    total += value
                    if i < len(partial_result) - 1:
                        partial += ", "
                partial += "]"
            else:
                # Parse the constant value
                total += int(part) * op
                partial += f"{part}"
        # Return the total as a string
        return f"{total} = {partial}"

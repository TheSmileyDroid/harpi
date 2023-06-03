import unittest
from src.modules.utils.dice_roller import DiceHandler, DiceRoller


class DeterministicDiceRoller(DiceRoller):
    def __init__(self) -> None:
        self.rolls: list[int] = []

    def roll(self, number_of_dice: int, number_of_sides: int) -> int:
        result: int = 0
        for _ in range(number_of_dice):
            result += self.rolls.pop(0)
            print(result)
        return result


class TestDiceHandler(unittest.TestCase):
    def setUp(self):
        self.dice_roller = DeterministicDiceRoller()
        self.handler = DiceHandler(self.dice_roller)

    def test_froll_simple(self):
        self.dice_roller.rolls = [4, 3]
        result = self.handler.froll("2d6")
        self.assertEqual(result, "7 = 2d6 [7]")

    def test_froll_with_addition(self):
        self.dice_roller.rolls = [4, 3]
        result = self.handler.froll("2d6+3")
        self.assertEqual(result, "10 = 2d6 [7] + 3")

    def test_froll_with_subtraction(self):
        self.dice_roller.rolls = [4, 3]
        result = self.handler.froll("2d6-3")
        self.assertEqual(result, "4 = 2d6 [7] - 3")

    def test_froll_with_multiple_dice(self):
        self.dice_roller.rolls = [4, 3, 5, 5, 6, 4]
        result = self.handler.froll("3#2d6")
        self.assertEqual(result, "7 = 2d6 [7]\n10 = 2d6 [10]\n10 = 2d6 [10]\n")


if __name__ == '__main__':
    unittest.main()

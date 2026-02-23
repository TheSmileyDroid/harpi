import random
from unittest.mock import patch

import pytest

from src.HarpiLib.math.parser import DiceParser, RollResult


class TestDiceParserInit:
    def test_creates_parser(self):
        parser = DiceParser()
        assert parser.operators is not None
        assert "+" in parser.operators
        assert "-" in parser.operators

    def test_operators_mapped_correctly(self):
        parser = DiceParser()
        assert parser.operators["+"](1, 2) == 3
        assert parser.operators["-"](5, 3) == 2
        assert parser.operators["*"](3, 4) == 12
        assert parser.operators["/"](10, 2) == 5
        assert parser.operators["//"](10, 3) == 3
        assert parser.operators["%"](10, 3) == 1
        assert parser.operators["^"](2, 3) == 8


class TestTokenize:
    def test_tokenize_simple_number(self):
        parser = DiceParser()
        tokens = parser.tokenize("5")
        assert tokens == ["5"]

    def test_tokenize_dice(self):
        parser = DiceParser()
        tokens = parser.tokenize("2d6")
        assert tokens == ["2d6"]

    def test_tokenize_dice_with_modifier(self):
        parser = DiceParser()
        tokens = parser.tokenize("2d6+5")
        assert tokens == ["2d6", "+", "5"]

    def test_tokenize_complex_expression(self):
        parser = DiceParser()
        tokens = parser.tokenize("2d6+3d4-1")
        assert tokens == ["2d6", "+", "3d4", "-", "1"]

    def test_tokenize_with_parentheses(self):
        parser = DiceParser()
        tokens = parser.tokenize("(2d6+3)*2")
        assert tokens == ["(", "2d6", "+", "3", ")", "*", "2"]

    def test_tokenize_float(self):
        parser = DiceParser()
        tokens = parser.tokenize("3.14+2.5")
        assert tokens == ["3.14", "+", "2.5"]

    def test_tokenize_floor_division(self):
        parser = DiceParser()
        tokens = parser.tokenize("10//3")
        assert tokens == ["10", "//", "3"]

    def test_tokenize_exponentiation(self):
        parser = DiceParser()
        tokens = parser.tokenize("2^3")
        assert tokens == ["2", "^", "3"]


class TestIsValidDiceString:
    def test_valid_simple_dice(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("1d6") is True
        assert parser.is_valid_dice_string("2d20") is True
        assert parser.is_valid_dice_string("10d8") is True

    def test_valid_advantage_dice(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("2#d6") is True
        assert parser.is_valid_dice_string("0#d20") is True

    def test_invalid_dice_string(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("abc") is False
        assert parser.is_valid_dice_string("1d") is False
        assert parser.is_valid_dice_string("d6") is False


class TestRollDice:
    def test_roll_single_die(self):
        parser = DiceParser()
        with patch.object(random, "randint", return_value=4):
            result = parser._roll_dice(
                type("Match", (), {"groups": lambda s: ("1", "6")})()
            )
            assert result.value == 4
            assert result.rolls == [([4], "1d6")]

    def test_roll_multiple_dice(self):
        parser = DiceParser()
        with patch.object(random, "randint", return_value=3):
            result = parser._roll_dice(
                type("Match", (), {"groups": lambda s: ("3", "6")})()
            )
            assert result.value == 9
            assert len(result.rolls[0][0]) == 3

    def test_roll_advantage(self):
        parser = DiceParser()
        rolls = [4, 6]
        with patch.object(random, "randint", side_effect=rolls):
            result = parser._roll_dice(
                type("Match", (), {"groups": lambda s: ("2#", "6")})()
            )
            assert result.value == 6
            assert len(result.rolls[0][0]) == 2

    def test_roll_disadvantage(self):
        parser = DiceParser()
        rolls = [4, 6]
        with patch.object(random, "randint", side_effect=rolls):
            result = parser._roll_dice(
                type("Match", (), {"groups": lambda s: ("0#", "6")})()
            )
            assert result.value == 4
            assert len(result.rolls[0][0]) == 2


class TestParsePrimary:
    def test_parse_number(self):
        parser = DiceParser()
        result = parser._parse_primary(["42"])
        assert result.value == 42
        assert result.rolls == []
        assert result.expression == "42"

    def test_parse_float(self):
        parser = DiceParser()
        result = parser._parse_primary(["3.5"])
        assert result.value == 3.5

    def test_parse_parentheses(self):
        parser = DiceParser()
        result = parser._parse_primary(["(", "5", ")"])
        assert result.value == 5

    def test_parse_empty_returns_zero(self):
        parser = DiceParser()
        result = parser._parse_primary([])
        assert result.value == 0


class TestParseAddition:
    def test_simple_addition(self):
        parser = DiceParser()
        result = parser._parse_addition(["3", "+", "5"])
        assert result.value == 8

    def test_simple_subtraction(self):
        parser = DiceParser()
        result = parser._parse_addition(["10", "-", "4"])
        assert result.value == 6

    def test_chained_addition(self):
        parser = DiceParser()
        result = parser._parse_addition(["1", "+", "2", "+", "3"])
        assert result.value == 6


class TestParseMultiplication:
    def test_simple_multiplication(self):
        parser = DiceParser()
        result = parser._parse_multiplication(["3", "*", "4"])
        assert result.value == 12

    def test_simple_division(self):
        parser = DiceParser()
        result = parser._parse_multiplication(["12", "/", "4"])
        assert result.value == 3

    def test_floor_division(self):
        parser = DiceParser()
        result = parser._parse_multiplication(["10", "//", "3"])
        assert result.value == 3

    def test_modulo(self):
        parser = DiceParser()
        result = parser._parse_multiplication(["10", "%", "3"])
        assert result.value == 1


class TestParseExponentiation:
    def test_simple_power(self):
        parser = DiceParser()
        result = parser._parse_exponentiation(["2", "^", "3"])
        assert result.value == 8

    def test_right_associative(self):
        parser = DiceParser()
        result = parser._parse_exponentiation(["2", "^", "3", "^", "2"])
        assert result.value == 512


class TestParse:
    def test_parse_simple_number(self):
        parser = DiceParser()
        result = parser.parse("5")
        assert result.value == 5

    def test_parse_simple_expression(self):
        parser = DiceParser()
        result = parser.parse("5+3")
        assert result.value == 8

    def test_operator_precedence(self):
        parser = DiceParser()
        result = parser.parse("2+3*4")
        assert result.value == 14

    def test_parentheses_override_precedence(self):
        parser = DiceParser()
        result = parser.parse("(2+3)*4")
        assert result.value == 20

    def test_empty_expression(self):
        parser = DiceParser()
        result = parser.parse("")
        assert result.value == 0


class TestRoll:
    def test_roll_returns_string(self):
        parser = DiceParser()
        result = parser.roll("3d6")
        assert isinstance(result, str)
        assert "Error" not in result

    def test_roll_with_invalid_dice_spec(self):
        parser = DiceParser()
        with pytest.raises(ValueError, match="Invalid dice specification"):
            parser._roll_dice(
                type("Match", (), {"groups": lambda s: ("-1", "6")})()
            )


class TestFormatResult:
    def test_format_simple_roll(self):
        parser = DiceParser()
        result = RollResult(10, [([5, 5], "2d6")], "10")
        formatted = parser._format_result(result, "2d6")
        assert "10" in formatted
        assert "2d6" in formatted

    def test_format_pure_math(self):
        parser = DiceParser()
        result = RollResult(8, [], "8")
        formatted = parser._format_result(result, "5+3")
        assert "8" in formatted
        assert "5+3" in formatted


class TestComplexExpressions:
    def test_nested_parentheses(self):
        parser = DiceParser()
        result = parser.parse("((2+3)*4)")
        assert result.value == 20

    def test_mixed_operations(self):
        parser = DiceParser()
        result = parser.parse("10+2*3-4")
        assert result.value == 12

    def test_complex_expression(self):
        parser = DiceParser()
        result = parser.parse("(5+3)*2-4/2")
        assert result.value == 14


class TestMismatchedParentheses:
    def test_missing_closing_paren(self):
        parser = DiceParser()
        try:
            parser.parse("(2+3")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Mismatched parentheses" in str(e)

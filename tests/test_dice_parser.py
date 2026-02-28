import random
from unittest.mock import patch

import pytest

from src.harpi_lib.math.parser import DiceParser, RollResult


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

    def test_tokenize_keep_highest(self):
        parser = DiceParser()
        tokens = parser.tokenize("4d6kh3")
        assert tokens == ["4d6kh3"]

    def test_tokenize_keep_lowest(self):
        parser = DiceParser()
        tokens = parser.tokenize("2d20kl1")
        assert tokens == ["2d20kl1"]

    def test_tokenize_fudge_dice(self):
        parser = DiceParser()
        tokens = parser.tokenize("4dF")
        assert tokens == ["4dF"]

    def test_tokenize_fudge_lowercase(self):
        parser = DiceParser()
        tokens = parser.tokenize("4df")
        assert tokens == ["4df"]

    def test_tokenize_fudge_with_modifier(self):
        parser = DiceParser()
        tokens = parser.tokenize("4dF+2")
        assert tokens == ["4dF", "+", "2"]

    def test_tokenize_keep_with_modifier(self):
        parser = DiceParser()
        tokens = parser.tokenize("4d6kh3+5")
        assert tokens == ["4d6kh3", "+", "5"]


class TestIsValidDiceString:
    def test_valid_simple_dice(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("1d6") is True
        assert parser.is_valid_dice_string("2d20") is True
        assert parser.is_valid_dice_string("10d8") is True

    def test_valid_keep_dice(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("4d6kh3") is True
        assert parser.is_valid_dice_string("2d20kl1") is True

    def test_valid_fudge_dice(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("4dF") is True
        assert parser.is_valid_dice_string("2df") is True

    def test_valid_compound_expressions(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("2d6+3") is True
        assert parser.is_valid_dice_string("1d6-1d6") is True
        assert parser.is_valid_dice_string("(2d6+3)*2") is True
        assert parser.is_valid_dice_string("2d6+1d8") is True

    def test_valid_repeat_syntax(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("2#d20") is True
        assert parser.is_valid_dice_string("2#d20+1d6") is True
        assert parser.is_valid_dice_string("3#d20kh1") is True
        assert parser.is_valid_dice_string("2#d20+5") is True

    def test_valid_bare_dX(self):
        """Bare dX (without leading count) should be accepted."""
        parser = DiceParser()
        assert parser.is_valid_dice_string("d20") is True
        assert parser.is_valid_dice_string("dF") is True
        assert parser.is_valid_dice_string("d6+3") is True

    def test_invalid_dice_string(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("abc") is False
        assert parser.is_valid_dice_string("1d") is False

    def test_invalid_pure_math(self):
        """Pure arithmetic without dice should not trigger auto-reply."""
        parser = DiceParser()
        assert parser.is_valid_dice_string("2+3") is False
        assert parser.is_valid_dice_string("42") is False

    def test_invalid_empty_or_whitespace(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("") is False
        assert parser.is_valid_dice_string("  ") is False

    def test_invalid_garbage(self):
        parser = DiceParser()
        assert parser.is_valid_dice_string("hello world") is False
        assert parser.is_valid_dice_string("#d20") is False


class TestRollDice:
    def _make_match(self, token: str) -> object:
        """Create a real regex match for _roll_dice."""
        parser = DiceParser()
        m = parser.dice_pattern.match(token)
        assert m is not None, f"Token {token!r} did not match dice_pattern"
        return m

    def test_roll_single_die(self):
        parser = DiceParser()
        with patch.object(random, "randint", return_value=4):
            result = parser._roll_dice(self._make_match("1d6"))
            assert result.value == 4
            assert result.rolls == [([4], "1d6", None)]

    def test_roll_multiple_dice(self):
        parser = DiceParser()
        with patch.object(random, "randint", return_value=3):
            result = parser._roll_dice(self._make_match("3d6"))
            assert result.value == 9
            assert len(result.rolls[0][0]) == 3

    def test_roll_keep_highest(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[3, 5, 1, 6]):
            result = parser._roll_dice(self._make_match("4d6kh3"))
            # Keep highest 3: 5, 3, 6 = 14
            assert result.value == 14
            kept_mask = result.rolls[0][2]
            assert kept_mask == [True, True, False, True]

    def test_roll_keep_lowest(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[15, 5]):
            result = parser._roll_dice(self._make_match("2d20kl1"))
            assert result.value == 5
            kept_mask = result.rolls[0][2]
            assert kept_mask == [False, True]

    def test_roll_fudge_dice(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[1, -1, 0, 1]):
            result = parser._roll_dice(self._make_match("4dF"))
            assert result.value == 1  # 1 + (-1) + 0 + 1
            assert result.rolls[0][0] == [1, -1, 0, 1]

    def test_invalid_dice_spec_raises(self):
        parser = DiceParser()
        with pytest.raises(ValueError, match="Invalid dice specification"):
            parser._roll_dice(self._make_match("1d0"))


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

    def test_parse_dice_with_keep_highest(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[3, 5, 1, 6]):
            result = parser.parse("4d6kh3+2")
            assert result.value == 16  # (5+3+6) + 2

    def test_parse_fudge_dice_with_modifier(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[1, -1, 0, 1]):
            result = parser.parse("4dF+3")
            assert result.value == 4  # 1+(-1)+0+1 + 3


class TestRoll:
    def test_roll_returns_string(self):
        parser = DiceParser()
        result = parser.roll("3d6")
        assert isinstance(result, str)
        assert "Error" not in result

    def test_roll_with_invalid_dice_spec(self):
        parser = DiceParser()
        result = parser.roll("1d0")
        assert result.startswith("Error:")


class TestFormatResult:
    def test_format_simple_roll(self):
        parser = DiceParser()
        result = RollResult(10, [([5, 5], "2d6", None)], "10")
        formatted = parser._format_result(result, "2d6")
        assert "10" in formatted
        assert "2d6" in formatted

    def test_format_pure_math(self):
        parser = DiceParser()
        result = RollResult(8, [], "8")
        formatted = parser._format_result(result, "5+3")
        assert "8" in formatted
        assert "5+3" in formatted

    def test_format_duplicate_dice_shows_different_values(self):
        """Bug 1 regression: 1d6-1d6 must show each die's own values."""
        parser = DiceParser()
        result = RollResult(
            2,
            [([4], "1d6", None), ([2], "1d6", None)],
            "4 - 2",
        )
        formatted = parser._format_result(result, "1d6-1d6")
        assert "[4]" in formatted
        assert "[2]" in formatted

    def test_format_bold_not_corrupted(self):
        """Bug 2 regression: ** bold markers must survive operator spacing."""
        parser = DiceParser()
        result = RollResult(6, [([6], "1d6", None)], "6")
        formatted = parser._format_result(result, "1d6")
        assert "**6**" in formatted
        # Must NOT contain "* * 6 * *"
        assert "* *" not in formatted

    def test_format_keep_highest_shows_strikethrough(self):
        parser = DiceParser()
        result = RollResult(
            14,
            [([3, 5, 1, 6], "4d6kh3", [True, True, False, True])],
            "4d6kh3",
        )
        formatted = parser._format_result(result, "4d6kh3")
        assert "~~1~~" in formatted  # dropped die
        assert "4d6kh3" in formatted

    def test_format_fudge_dice_shows_symbols(self):
        parser = DiceParser()
        result = RollResult(1, [([1, -1, 0, 1], "4dF", None)], "4dF")
        formatted = parser._format_result(result, "4dF")
        assert "+" in formatted
        assert "-" in formatted
        assert "4dF" in formatted

    def test_format_floor_division_spaced(self):
        """Floor division is spaced when dice are present."""
        parser = DiceParser()
        result = RollResult(1, [([3], "1d6", None)], "1d6")
        formatted = parser._format_result(result, "1d6//3")
        assert "1d6 // 3" in formatted


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
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Mismatched parentheses" in str(e)

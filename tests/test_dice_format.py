"""Tests for DiceParser formatting, repeat (#), keep (kh/kl), and fudge (dF) features."""

import random
from unittest.mock import patch

from src.harpi_lib.math.parser import DiceParser, RollResult


# === Repeat (#) operator ===


class TestRepeatOperator:
    """N#expression evaluates the expression N times independently."""

    def test_repeat_basic(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[10, 15]):
            result = parser.roll("2#1d20")
        lines = result.strip().split("\n")
        assert len(lines) == 3  # 2 rolls + Max line
        assert "Max:" in lines[-1]

    def test_repeat_shows_max_only_when_count_gt_1(self):
        parser = DiceParser()
        with patch.object(random, "randint", return_value=12):
            result = parser.roll("1#1d20")
        assert "Max:" not in result
        assert "12" in result

    def test_repeat_with_modifier(self):
        """2#d20+5 should show each roll with the +5 applied."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[10, 18]):
            result = parser.roll("2#d20+5")
        assert "15" in result  # 10+5
        assert "23" in result  # 18+5
        assert "Max: 23" in result

    def test_repeat_with_compound_expression(self):
        """2#d20+1d6 should work — each repetition rolls d20 and d6 independently."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[10, 3, 18, 5]):
            result = parser.roll("2#d20+1d6")
        lines = result.strip().split("\n")
        assert len(lines) == 3  # 2 rolls + Max
        assert "13" in lines[0]  # 10+3
        assert "23" in lines[1]  # 18+5
        assert "Max: 23" in lines[2]

    def test_repeat_normalizes_bare_d(self):
        """2#d20 (no leading 1) is normalized to 2#1d20."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[4, 17]):
            result = parser.roll("2#d20")
        assert "4" in result
        assert "17" in result
        assert "Max: 17" in result

    def test_repeat_zero_count(self):
        parser = DiceParser()
        result = parser.roll("0#1d20")
        assert "Error:" in result

    def test_repeat_with_keep_highest(self):
        """3#4d6kh3 should work."""
        parser = DiceParser()
        with patch.object(
            random,
            "randint",
            side_effect=[3, 5, 1, 6, 2, 4, 3, 5, 6, 1, 2, 4],
        ):
            result = parser.roll("3#4d6kh3")
        lines = result.strip().split("\n")
        assert len(lines) == 4  # 3 rolls + Max
        assert "Max:" in lines[-1]


# === Keep highest / lowest ===


class TestKeepHighest:
    def test_kh_basic(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[3, 5, 1, 6]):
            result = parser.parse("4d6kh3")
        assert result.value == 14  # 3+5+6

    def test_kh_format_shows_dropped(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[3, 5, 1, 6]):
            output = parser.roll("4d6kh3")
        assert "~~" in output  # dropped die has strikethrough
        assert "4d6kh3" in output

    def test_kh_advantage(self):
        """2d20kh1 = advantage (keep highest of 2d20)."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[8, 15]):
            result = parser.parse("2d20kh1")
        assert result.value == 15

    def test_kh_more_than_count(self):
        """Keep count exceeding dice count keeps all."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[3, 5]):
            result = parser.parse("2d6kh5")
        assert result.value == 8  # all kept


class TestKeepLowest:
    def test_kl_basic(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[15, 5]):
            result = parser.parse("2d20kl1")
        assert result.value == 5

    def test_kl_format_shows_dropped(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[15, 5]):
            output = parser.roll("2d20kl1")
        assert "~~" in output
        assert "2d20kl1" in output

    def test_kl_disadvantage(self):
        """2d20kl1 = disadvantage (keep lowest of 2d20)."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[18, 3]):
            result = parser.parse("2d20kl1")
        assert result.value == 3


# === Fudge / Fate dice ===


class TestFudgeDice:
    def test_basic_fudge(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[1, -1, 0, 1]):
            result = parser.parse("4dF")
        assert result.value == 1  # 1+(-1)+0+1

    def test_fudge_lowercase(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[0, 0]):
            result = parser.parse("2df")
        assert result.value == 0

    def test_fudge_format_shows_symbols(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[1, -1, 0]):
            output = parser.roll("3dF")
        assert "+" in output
        assert "-" in output
        assert "3dF" in output

    def test_fudge_with_modifier(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[1, 1, -1, 0]):
            result = parser.parse("4dF+3")
        assert result.value == 4  # 1+1+(-1)+0 + 3

    def test_fudge_with_keep_highest(self):
        parser = DiceParser()
        with patch.object(random, "choice", side_effect=[1, -1, 0, 1]):
            result = parser.parse("4dFkh2")
        assert result.value == 2  # keep the two +1s


# === Operator spacing ===


class TestSpaceOperators:
    def test_bold_preserved(self):
        """Bold markers ** must not be split by spacing."""
        result = DiceParser._space_operators("[**6**] 1d6*2")
        assert "**6**" in result
        assert "* *" not in result

    def test_floor_division_spaced(self):
        result = DiceParser._space_operators("10//3")
        assert "10 // 3" == result

    def test_parens_tightened(self):
        result = DiceParser._space_operators("(5+3)*2")
        assert result == "(5 + 3) * 2"


# === End-to-end roll() tests ===


class TestRollEndToEnd:
    def test_roll_error_on_exception(self):
        parser = DiceParser()
        result = parser.roll("(2+3")
        assert result.startswith("Error:")

    def test_roll_simple_dice(self):
        parser = DiceParser()
        with patch.object(random, "randint", return_value=4):
            result = parser.roll("1d6+3")
        assert "7" in result
        assert "1d6" in result

    def test_roll_duplicate_dice_independent(self):
        """Bug 1: 1d6-1d6 must show each die's own roll value."""
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[4, 2]):
            result = parser.roll("1d6-1d6")
        assert "[4]" in result
        assert "[2]" in result
        assert "2" in result  # 4-2=2


class TestSafeEval:
    def test_evaluates_arithmetic(self):
        parser = DiceParser()
        assert parser._safe_eval("3+5") == 8

    def test_evaluates_complex_expression(self):
        parser = DiceParser()
        assert parser._safe_eval("(2+3)*4") == 20


class TestParsePrimaryError:
    def test_unexpected_token_raises(self):
        parser = DiceParser()
        import pytest

        with pytest.raises(ValueError, match="Unexpected token"):
            parser._parse_primary(["abc"])

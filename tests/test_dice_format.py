"""Tests for DiceParser _format_result with # (advantage/disadvantage) notation
and other uncovered parser paths."""

import random
from unittest.mock import patch

from src.harpi_lib.math.parser import DiceParser, RollResult


class TestFormatResultAdvantage:
    """Tests for the _format_result # branch (advantage rolls)."""

    def test_advantage_basic(self):
        """2#d20 → roll 2d20, show each, report Max."""
        parser = DiceParser()
        result = RollResult(15, [([10, 15], "2#d20")], "2#d20")
        formatted = parser._format_result(result, "2#d20")
        assert "Max:" in formatted
        assert "15" in formatted
        # Should show individual rolls
        assert "1d20" in formatted

    def test_advantage_bolds_max_roll(self):
        """A roll equal to die sides should be bolded."""
        parser = DiceParser()
        result = RollResult(20, [([20, 5], "2#d20")], "2#d20")
        formatted = parser._format_result(result, "2#d20")
        assert "**20**" in formatted  # max roll bolded

    def test_advantage_with_modifier(self):
        """2#d20+5 → each roll shows +5, Max includes modifier."""
        parser = DiceParser()
        result = RollResult(15, [([10, 15], "2#d20")], "2#d20")
        formatted = parser._format_result(result, "2#d20+5")
        assert "Max:" in formatted
        assert "+5" in formatted

    def test_disadvantage_basic(self):
        """0#d20 → roll 2d20, show each, report Min."""
        parser = DiceParser()
        result = RollResult(5, [([5, 15], "0#d20")], "0#d20")
        formatted = parser._format_result(result, "0#d20")
        assert "Min:" in formatted
        assert "5" in formatted

    def test_disadvantage_bolds_max_roll(self):
        """Even in disadvantage, a natural max roll is bolded."""
        parser = DiceParser()
        result = RollResult(3, [([20, 3], "0#d20")], "0#d20")
        formatted = parser._format_result(result, "0#d20")
        assert "**20**" in formatted
        assert "Min:" in formatted

    def test_disadvantage_with_modifier(self):
        """0#d20+3 → Min should include the modifier."""
        parser = DiceParser()
        result = RollResult(5, [([5, 15], "0#d20")], "0#d20")
        formatted = parser._format_result(result, "0#d20+3")
        assert "Min:" in formatted
        assert "+3" in formatted

    def test_single_advantage_roll_no_max_line(self):
        """1#d20 → only 1 roll, no Max line (count <= 1)."""
        parser = DiceParser()
        result = RollResult(12, [([12], "1#d20")], "1#d20")
        formatted = parser._format_result(result, "1#d20")
        assert "Max:" not in formatted
        assert "12" in formatted

    def test_advantage_no_modifier(self):
        """2#d6 with no rest-of-expr → just rolls, no math suffix."""
        parser = DiceParser()
        result = RollResult(5, [([3, 5], "2#d6")], "2#d6")
        formatted = parser._format_result(result, "2#d6")
        lines = formatted.strip().split("\n")
        # Should have 2 roll lines + 1 Max line
        assert len(lines) == 3
        assert "Max:" in lines[-1]


class TestFormatResultDisadvantageWithModifier:
    def test_disadvantage_modifier_applied_to_min(self):
        """0#d20+5 → Min line should be min_roll + 5."""
        parser = DiceParser()
        result = RollResult(3, [([3, 18], "0#d20")], "0#d20")
        formatted = parser._format_result(result, "0#d20+5")
        # Min should be 3+5 = 8
        assert "Min: 8" in formatted

    def test_advantage_modifier_applied_to_max(self):
        """2#d20+5 → Max line should be max_roll + 5."""
        parser = DiceParser()
        result = RollResult(18, [([10, 18], "2#d20")], "2#d20")
        formatted = parser._format_result(result, "2#d20+5")
        # Max should be 18+5 = 23
        assert "Max: 23" in formatted


class TestRollEndToEnd:
    """End-to-end tests for roll() with # notation (goes through parse + format)."""

    def test_roll_advantage_end_to_end(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[10, 15]):
            result = parser.roll("2#d20")
        assert "Max:" in result
        assert "Error" not in result

    def test_roll_disadvantage_end_to_end(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[5, 15]):
            result = parser.roll("0#d20")
        assert "Min:" in result
        assert "Error" not in result

    def test_roll_advantage_with_modifier_end_to_end(self):
        parser = DiceParser()
        with patch.object(random, "randint", side_effect=[10, 18]):
            result = parser.roll("2#d20+5")
        assert "Max:" in result
        assert "+5" in result


class TestRollErrorPath:
    def test_roll_returns_error_on_exception(self):
        parser = DiceParser()
        # Mismatched parentheses trigger ValueError inside parse()
        result = parser.roll("(2+3")
        assert result.startswith("Error:")


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

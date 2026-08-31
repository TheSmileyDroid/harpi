"""Deterministic tests for the dice notation parser."""

import pytest

from src.harpi_lib.math.parser import (
    _FUDGE_SYMBOLS,
    DiceParser,
    RollResult,
)


@pytest.fixture
def parser():
    return DiceParser()


def _patch_random(monkeypatch, values):
    """Make randint/choice replay *values* in order, then repeat the last."""
    seq = iter(values)
    last = values[-1]

    def fake_randint(_low, _high):
        return next(seq, last)

    def fake_choice(options):
        return next(seq, last)

    monkeypatch.setattr(
        "src.harpi_lib.math.parser.random.randint", fake_randint
    )
    monkeypatch.setattr("src.harpi_lib.math.parser.random.choice", fake_choice)


def test_tokenize_splits_dice_numbers_and_operators(parser):
    assert parser.tokenize("2d6+3") == ["2d6", "+", "3"]
    assert parser.tokenize("1d20kh2//2") == ["1d20kh2", "//", "2"]
    assert parser.tokenize("(2d6+3)*2") == [
        "(",
        "2d6",
        "+",
        "3",
        ")",
        "*",
        "2",
    ]
    assert parser.tokenize("4dF") == ["4dF"]


def test_parse_plain_dice_with_monotonic_rolls(parser, monkeypatch):
    _patch_random(monkeypatch, [3, 5])
    result = parser.parse("2d6")
    assert result.value == 8
    assert result.rolls == [([3, 5], "2d6", None)]
    assert result.expression == "2d6"


def test_parse_arithmetic_precedence(parser):
    assert parser.parse("2+3*4").value == 14
    assert parser.parse("(2+3)*2").value == 10
    assert parser.parse("2^3").value == 8
    assert parser.parse("2^3^2").value == 512
    assert parser.parse("7//2").value == 3
    assert parser.parse("7%3").value == 1
    assert parser.parse("7/2").value == pytest.approx(3.5)
    assert parser.parse("10-4-3").value == 3


def test_parse_combines_rolls_and_expression(parser, monkeypatch):
    _patch_random(monkeypatch, [4])
    result = parser.parse("1d6+2*3")
    assert result.value == 10
    assert result.expression == "1d6 + 2 * 3"


def test_parse_empty_tokens_returns_zero(parser):
    assert parser.parse("") == RollResult(0, [], "")


def test_parse_primary_without_tokens_returns_zero(parser):
    assert parser._parse_primary([]) == RollResult(0, [], "")


def test_parse_primary_float_literal(parser):
    result = parser.parse("2.5+1")
    assert result.value == pytest.approx(3.5)


def test_parse_primary_unexpected_token_raises(parser):
    with pytest.raises(ValueError, match="Unexpected token"):
        parser.parse(")2d6")


def test_parse_primary_mismatched_parentheses_raises(parser):
    with pytest.raises(ValueError, match="Mismatched parentheses"):
        parser.parse("(2d6")


def test_roll_dice_invalid_sides_raises(parser):
    with pytest.raises(ValueError, match="Invalid dice"):
        parser.parse("1d0")


def test_roll_dice_negative_count_is_not_a_dice_token(parser):
    assert parser.roll("-1d6") == "Error: Unexpected token: -"


def test_roll_all_dice_zero_count_gives_empty(parser, monkeypatch):
    _patch_random(monkeypatch, [1])
    assert parser._roll_all_dice(0, "6") == []


def test_roll_all_dice_fudge_uses_choice(parser, monkeypatch):
    _patch_random(monkeypatch, [-1, 1])
    assert parser._roll_all_dice(2, "F") == [-1, 1]


def test_roll_all_dice_negative_count_raises(parser):
    with pytest.raises(ValueError, match="Invalid dice"):
        parser._roll_all_dice(-1, "6")


def test_roll_all_dice_rejects_zero_sides(parser):
    with pytest.raises(ValueError, match="Invalid dice"):
        parser._roll_all_dice(1, "0")


def test_apply_keep_filter_without_mode_keeps_all(parser):
    mask, total = parser._apply_keep_filter(None, None, [2, 5])
    assert mask is None
    assert total == 7


def test_apply_keep_filter_kh(parser):
    mask, total = parser._apply_keep_filter("kh", "2", [1, 6, 4])
    assert mask == [False, True, True]
    assert total == 10


def test_apply_keep_filter_kl(parser):
    mask, total = parser._apply_keep_filter("kl", "1", [9, 3, 7])
    assert mask == [False, True, False]
    assert total == 3


def test_apply_keep_filter_keeps_all_when_count_exceeds_dice(parser):
    mask, total = parser._apply_keep_filter("kh", "5", [4, 2])
    assert mask == [True, True]
    assert total == 6


def test_roll_kh_formats_dropped_dice(parser, monkeypatch):
    _patch_random(monkeypatch, [1, 6, 5, 3])
    result = parser.parse("4d6kh3")
    assert result.value == 14
    assert result.rolls == [
        ([1, 6, 5, 3], "4d6kh3", [False, True, True, True])
    ]
    formatted = parser._format_result(result, "4d6kh3")
    assert formatted == "` 14 ` ⟵ [~~1~~, **6**, 5, 3] 4d6kh3"


def test_roll_kl_formats_dropped_dice(parser, monkeypatch):
    _patch_random(monkeypatch, [15, 7])
    result = parser.parse("2d20kl1")
    assert result.value == 7
    formatted = parser._format_result(result, "2d20kl1")
    assert formatted == "` 7 ` ⟵ [~~15~~, 7] 2d20kl1"


def test_roll_kh_beyond_dice_count_keeps_all(parser, monkeypatch):
    _patch_random(monkeypatch, [4, 2])
    formatted = parser.roll("2d6kh5")
    assert formatted == "` 6 ` ⟵ [4, 2] 2d6kh5"


def test_roll_fudge_formats_symbols(parser, monkeypatch):
    _patch_random(monkeypatch, [1, -1, 0, 1])
    result = parser.parse("4dF")
    assert result.value == 1
    formatted = parser._format_result(result, "4dF")
    assert formatted == "` 1 ` ⟵ [ + , - , , + ] 4dF"
    assert _FUDGE_SYMBOLS[0].isspace()
    assert _FUDGE_SYMBOLS[0] not in formatted


def test_roll_fudge_kh_formats_dropped_symbols(parser, monkeypatch):
    _patch_random(monkeypatch, [1, 1, -1, 0])
    result = parser.parse("4dFkh2")
    assert result.value == 2
    formatted = parser._format_result(result, "4dFkh2")
    assert formatted == "` 2 ` ⟵ [ + , + , ~~ - ~~, ~~ ~~] 4dFkh2"


def test_roll_max_value_is_bolded(parser, monkeypatch):
    _patch_random(monkeypatch, [6, 2])
    formatted = parser.roll("2d6")
    assert formatted == "` 8 ` ⟵ [**6**, 2] 2d6"


def test_roll_without_dice_formats_bare_value(parser):
    formatted = parser.roll("(2+3)")
    assert formatted == "` 5 ` ⟵ (2+3)"


def test_roll_error_returns_error_string(parser):
    assert parser.roll("1d0") == "Error: Invalid dice specification"
    assert parser.roll(")2d6") == "Error: Unexpected token: )"
    assert parser.roll("(2d6") == "Error: Mismatched parentheses"


def test_roll_repeated_runs_expression_n_times(parser, monkeypatch):
    _patch_random(monkeypatch, [10, 4])
    output = parser.roll("2#d20+5")
    lines = output.split("\n")
    assert lines == [
        "` 15 ` ⟵ [10] 1d20 + 5",
        "` 9 ` ⟵ [4] 1d20 + 5",
        "Max: 15",
    ]


def test_roll_repeated_once_has_no_max_line(parser, monkeypatch):
    _patch_random(monkeypatch, [7])
    output = parser.roll("1#d20")
    assert output == "` 7 ` ⟵ [7] 1d20"


def test_roll_repeated_rejects_non_positive_count(parser):
    assert parser.roll("0#d20") == "Error: repeat count must be positive"


def test_format_result_without_rolls_shows_value(parser):
    result = RollResult(5, [], "")
    assert parser._format_result(result, "5") == "` 5 ` ⟵ 5"


def test_format_result_disambiguates_repeated_notation(parser, monkeypatch):
    _patch_random(monkeypatch, [3, 5])
    formatted = parser.roll("1d6-1d6")
    assert formatted == "` -2 ` ⟵ [3] 1d6 - [5] 1d6"


def test_space_operators_preserves_bold(parser):
    assert DiceParser._space_operators("[**6**]+3") == "[**6**] + 3"


def test_space_operators_spaces_floor_div(parser):
    assert DiceParser._space_operators("6//2") == "6 // 2"


def test_space_operators_tightens_parens(parser):
    assert DiceParser._space_operators("( 2d6 + 3 )") == "(2d6 + 3)"


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2d6+3", True),
        ("1d6-1d6", True),
        ("(2d6+3)*2", True),
        ("3#2d6", True),
        ("d6", True),
        ("dF", True),
        ("4dFkh2", True),
        ("2+3", False),
        ("", False),
        ("   ", False),
        ("2d6;", False),
        ("abc", False),
    ],
)
def test_is_valid_dice_string(parser, expression, expected):
    assert parser.is_valid_dice_string(expression) is expected

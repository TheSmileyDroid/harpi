"""Dice expression parser with recursive descent evaluation.

Supported notation
------------------
* Basic dice: ``2d6``, ``1d20+5``, ``(2d6+3)*2``
* Keep highest/lowest: ``4d6kh3`` (keep highest 3), ``2d20kl1`` (keep lowest 1)
* Fudge/Fate dice: ``4dF`` (each die is -1, 0, or +1)
* Repeat operator: ``3#d20+5`` (roll ``d20+5`` three times independently)
* Arithmetic: ``+``, ``-``, ``*``, ``/``, ``//``, ``%``, ``^``, ``()``
"""

import operator
import random
import re
from collections import namedtuple

# ``rolls`` is a list of ``(individual_values, notation, kept_mask | None)``
# tuples.  ``kept_mask`` is a list[bool] the same length as
# ``individual_values`` indicating which dice were kept (for kh/kl);
# ``None`` means all dice were kept.
RollResult = namedtuple("RollResult", ["value", "rolls", "expression"])

_FUDGE_SYMBOLS = {-1: "-", 0: "\u2007", 1: "+"}


class DiceParser:
    """Recursive descent parser for dice notation expressions (e.g. '2d6+3')."""

    def __init__(self) -> None:
        self.operators: dict[str, object] = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "//": operator.floordiv,
            "/": operator.truediv,
            "%": operator.mod,
            "^": operator.pow,
        }

        # Dice pattern: NdX, NdXkhY, NdXklY, NdF
        # Groups: (count, sides_or_F, optional_keep_mode, optional_keep_count)
        self.dice_pattern = re.compile(r"(\d+)d([fF]|\d+)(?:(kh|kl)(\d+))?$")
        self.token_pattern = re.compile(
            r"(\d+d(?:[fF]|\d+)(?:(?:kh|kl)\d+)?|\d+\.\d+|\d+|\/\/|[\+\-\*\/\(\)\^\%])"
        )

    def tokenize(self, expression: str) -> list[str]:
        """Convert the expression string into tokens."""
        return self.token_pattern.findall(expression)

    def parse(self, expression: str) -> RollResult:
        """Parse and evaluate a dice expression (single evaluation)."""
        tokens = self.tokenize(expression)
        return self._evaluate_expression(tokens)

    def is_valid_dice_string(self, expression: str) -> bool:
        """Check if the string is a valid dice expression.

        Returns ``True`` when *expression* is something the parser can
        evaluate **and** it contains at least one dice token (``NdX``,
        ``NdF``, ``NdXkhY``, etc.).  This accepts compound expressions
        like ``2d6+3``, ``1d6-1d6``, ``(2d6+3)*2``, the ``N#expr``
        repeat syntax, and bare ``dX`` shorthand.

        Pure arithmetic (``2+3``) returns ``False`` so the bot does not
        auto-reply to every number in chat.
        """
        if not expression or not expression.strip():
            return False

        expr = expression.strip()

        # Strip optional N# repeat prefix
        repeat_match = re.match(r"(\d+)#(.+)$", expr)
        if repeat_match:
            expr = repeat_match.group(2)

        # Normalize bare dX / dF → 1dX / 1dF so the tokenizer picks them up
        expr = re.sub(r"\bd(\d+|[fF])", r"1d\1", expr)

        # Tokenize and verify the tokens fully reconstruct the expression
        # (i.e. no unrecognized characters were silently skipped).
        tokens = self.tokenize(expr)
        if not tokens:
            return False

        if "".join(tokens) != expr.replace(" ", ""):
            return False

        # Must contain at least one dice token
        return any(self.dice_pattern.match(t) for t in tokens)

    # ------------------------------------------------------------------
    # Recursive descent parser
    # ------------------------------------------------------------------

    def _evaluate_expression(self, tokens: list[str]) -> RollResult:
        """Evaluate the expression using recursive descent parsing."""
        if not tokens:
            return RollResult(0, [], "")
        return self._parse_addition(tokens)

    def _parse_addition(self, tokens: list[str]) -> RollResult:
        """Parse addition and subtraction."""
        left = self._parse_multiplication(tokens)

        while tokens and tokens[0] in ("+", "-"):
            op = tokens.pop(0)
            right = self._parse_multiplication(tokens)

            result = self.operators[op](left.value, right.value)
            combined_rolls = left.rolls + right.rolls
            combined_expression = f"{left.expression} {op} {right.expression}"
            left = RollResult(result, combined_rolls, combined_expression)

        return left

    def _parse_multiplication(self, tokens: list[str]) -> RollResult:
        """Parse multiplication, division, and modulo."""
        left = self._parse_exponentiation(tokens)

        while tokens and tokens[0] in ("*", "/", "//", "%"):
            op = tokens.pop(0)
            right = self._parse_exponentiation(tokens)

            result = self.operators[op](left.value, right.value)
            combined_rolls = left.rolls + right.rolls
            combined_expression = f"{left.expression} {op} {right.expression}"
            left = RollResult(result, combined_rolls, combined_expression)

        return left

    def _parse_exponentiation(self, tokens: list[str]) -> RollResult:
        """Parse exponentiation (right-associative)."""
        left = self._parse_primary(tokens)

        if tokens and tokens[0] == "^":
            tokens.pop(0)
            right = self._parse_exponentiation(tokens)

            result = self.operators["^"](left.value, right.value)
            combined_rolls = left.rolls + right.rolls
            combined_expression = f"{left.expression} ^ {right.expression}"
            return RollResult(result, combined_rolls, combined_expression)

        return left

    def _parse_primary(self, tokens: list[str]) -> RollResult:
        """Parse primary expressions (numbers, dice rolls, parentheses)."""
        if not tokens:
            return RollResult(0, [], "")

        token = tokens.pop(0)

        # Parenthesized sub-expression
        if token == "(":
            result = self._evaluate_expression(tokens)
            if tokens and tokens[0] == ")":
                tokens.pop(0)
            else:
                raise ValueError("Mismatched parentheses")
            return RollResult(
                result.value, result.rolls, f"({result.expression})"
            )

        # Dice roll
        dice_match = self.dice_pattern.match(token)
        if dice_match:
            return self._roll_dice(dice_match)

        # Number literal
        try:
            value = float(token)
            if value.is_integer():
                value = int(value)
            return RollResult(value, [], str(value))
        except ValueError:
            raise ValueError(f"Unexpected token: {token}")

    # ------------------------------------------------------------------
    # Dice rolling
    # ------------------------------------------------------------------

    def _roll_dice(self, dice_match: re.Match[str]) -> RollResult:
        """Roll dice based on the matched notation.

        Supports: NdX, NdXkhY, NdXklY, NdF.
        """
        count_str, sides_str, keep_mode, keep_count_str = dice_match.groups()
        count = int(count_str)
        is_fudge = sides_str.upper() == "F"
        original_notation = dice_match.group(0)

        if is_fudge:
            sides = 0  # not used for range, just for max-bold check
            rolls = [random.choice([-1, 0, 1]) for _ in range(count)]
        else:
            sides = int(sides_str)
            if sides <= 0 or count < 0:
                raise ValueError("Invalid dice specification")
            rolls = [random.randint(1, sides) for _ in range(count)]

        # Keep-highest / keep-lowest filtering
        kept_mask: list[bool] | None = None
        if keep_mode and keep_count_str:
            keep_n = int(keep_count_str)
            if keep_n > count:
                keep_n = count
            if keep_mode == "kh":
                # Indices of the highest keep_n values
                sorted_indices = sorted(
                    range(count), key=lambda i: rolls[i], reverse=True
                )
            else:  # kl
                sorted_indices = sorted(range(count), key=lambda i: rolls[i])
            kept_indices = set(sorted_indices[:keep_n])
            kept_mask = [i in kept_indices for i in range(count)]
            total = sum(r for r, k in zip(rolls, kept_mask) if k)
        else:
            total = sum(rolls)

        return RollResult(
            total, [(rolls, original_notation, kept_mask)], original_notation
        )

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def roll(self, expression: str) -> str:
        """Roll dice and evaluate the expression, returning formatted output.

        Handles the ``N#expression`` repeat operator at this level:
        if the expression starts with ``N#``, evaluate the rest N times
        independently and display each result.
        """
        try:
            repeat_match = re.match(r"(\d+)#(.+)$", expression)
            if repeat_match:
                return self._roll_repeated(
                    int(repeat_match.group(1)), repeat_match.group(2)
                )
            result = self.parse(expression)
            return self._format_result(result, expression)
        except Exception as e:
            return f"Error: {str(e)}"

    def _roll_repeated(self, count: int, sub_expression: str) -> str:
        """Evaluate *sub_expression* *count* times and format all results."""
        if count <= 0:
            return "Error: repeat count must be positive"

        # Normalize bare "dX" to "1dX" so the tokenizer picks it up
        sub_expression = re.sub(r"\bd(\d+|[fF])", r"1d\1", sub_expression)

        lines: list[str] = []
        values: list[int | float] = []
        for _ in range(count):
            result = self.parse(sub_expression)
            values.append(result.value)
            lines.append(self._format_result(result, sub_expression))

        if count > 1:
            lines.append(f"Max: {max(values)}")

        return "\n".join(lines)

    def _safe_eval(self, expression: str) -> int | float:
        """Safely evaluate a pure arithmetic expression using the parser.

        This avoids using Python's built-in eval() which can execute
        arbitrary code. Only supports the operators defined in self.operators.

        Raises:
            ValueError: If the expression contains invalid tokens.
        """
        result = self.parse(expression)
        return result.value

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_result(
        self, result: RollResult, original_expression: str
    ) -> str:
        """Format a single ``RollResult`` for display."""

        # Pure math (no dice)
        if not result.rolls:
            return f"` {result.value} ` ⟵ {original_expression}"

        # Build the formatted expression by replacing each dice token
        # left-to-right with its individual roll values.
        # We use placeholder tokens to prevent already-replaced text from
        # being matched again when the same notation appears multiple times
        # (e.g. "1d6-1d6" — each 1d6 must get its own roll values).
        placeholders: list[tuple[str, str]] = []
        formatted_expr = original_expression
        for i, (rolls, notation, kept_mask) in enumerate(result.rolls):
            formatted_roll = self._format_single_dice(
                rolls, notation, kept_mask
            )
            placeholder = f"\x00DICE{i}\x00"
            placeholders.append((placeholder, formatted_roll))
            formatted_expr = formatted_expr.replace(notation, placeholder, 1)

        # Restore placeholders with actual formatted values
        for placeholder, formatted_roll in placeholders:
            formatted_expr = formatted_expr.replace(
                placeholder, formatted_roll
            )

        # Add spaces around arithmetic operators for readability, but
        # protect bold markers (**) from being treated as multiplication.
        formatted_expr = self._space_operators(formatted_expr)

        return f"` {result.value} ` ⟵ {formatted_expr}"

    def _format_single_dice(
        self,
        rolls: list[int],
        notation: str,
        kept_mask: list[bool] | None,
    ) -> str:
        """Format the roll values for a single dice group.

        Returns a string like ``[3, **6**] 2d6`` or ``[-, +, +] 3dF``.
        Dropped dice (from kh/kl) are shown with strikethrough.
        """
        is_fudge = "d" in notation and notation.split("d", 1)[
            1
        ].upper().startswith("F")

        if is_fudge:
            # Fudge dice: show symbols
            parts: list[str] = []
            for i, r in enumerate(rolls):
                sym = _FUDGE_SYMBOLS[r]
                kept = kept_mask[i] if kept_mask else True
                if not kept:
                    parts.append(f"~~{sym}~~")
                else:
                    parts.append(sym)
            roll_str = f"[{', '.join(parts)}]"
        else:
            # Extract sides for max-bold detection
            sides = self._extract_sides(notation)
            parts = []
            for i, r in enumerate(rolls):
                kept = kept_mask[i] if kept_mask else True
                if r == sides:
                    text = f"**{r}**"
                else:
                    text = str(r)
                if not kept:
                    text = f"~~{text}~~"
                parts.append(text)
            roll_str = f"[{', '.join(parts)}]"

        # Append the notation label (e.g. "2d6", "4d6kh3", "4dF")
        return f"{roll_str} {notation}"

    @staticmethod
    def _extract_sides(notation: str) -> int:
        """Extract the number of sides from a notation like '2d6kh1'."""
        m = re.search(r"d(\d+)", notation)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _space_operators(expr: str) -> str:
        """Add spaces around arithmetic operators without corrupting bold ``**`` markers.

        Strategy: temporarily replace multi-char sequences (``**`` bold,
        ``//`` floor-div) with placeholders, space the remaining single-char
        operators, then restore.
        """
        bold_ph = "\x00BOLD\x00"
        fdiv_ph = "\x00FDIV\x00"
        expr = expr.replace("**", bold_ph)
        expr = expr.replace("//", fdiv_ph)

        # Space single-char operators
        for op in ("+", "-", "*", "/", "%", "^"):
            expr = expr.replace(op, f" {op} ")

        # Clean up multiple spaces
        expr = re.sub(r"\s+", " ", expr).strip()
        # Tighten parens
        expr = expr.replace("( ", "(").replace(" )", ")")

        expr = expr.replace(bold_ph, "**")
        expr = expr.replace(fdiv_ph, " // ")
        return expr

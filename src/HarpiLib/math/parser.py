import operator
import random
import re
from collections import namedtuple

# Define a Roll result for storing and formatting dice results
RollResult = namedtuple("RollResult", ["value", "rolls", "expression"])


class DiceParser:
    def __init__(self):
        self.operators = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "//": operator.floordiv,
            "/": operator.truediv,
            "%": operator.mod,
            "^": operator.pow,
        }

        # Define regex patterns
        self.dice_pattern = re.compile(r"(\d+)#?d(\d+)")
        self.token_pattern = re.compile(
            r"(\d+\#?d\d+|\d+\.\d+|\d+|\/\/|[\+\-\*\/\(\)\^\%])"
        )

    def tokenize(self, expression):
        """Convert the expression string into tokens"""
        return self.token_pattern.findall(expression)

    def parse(self, expression):
        """Parse and evaluate the dice expression"""
        tokens = self.tokenize(expression)
        return self._evaluate_expression(tokens)

    def is_valid_dice_string(self, expression):
        """Check if the string is a valid dice expression"""
        return bool(self.dice_pattern.match(expression))

    def _evaluate_expression(self, tokens):
        """Evaluate the expression using recursive descent parsing"""
        # Handle an empty token list
        if not tokens:
            return RollResult(0, [], "")

        return self._parse_addition(tokens)

    def _parse_addition(self, tokens):
        """Parse addition and subtraction"""
        left = self._parse_multiplication(tokens)

        while tokens and tokens[0] in ("+", "-"):
            op = tokens.pop(0)
            right = self._parse_multiplication(tokens)

            left_val = left.value
            right_val = right.value
            result = self.operators[op](left_val, right_val)

            # Combine roll details
            combined_rolls = left.rolls + right.rolls
            combined_expression = f"{left.expression} {op} {right.expression}"

            left = RollResult(result, combined_rolls, combined_expression)

        return left

    def _parse_multiplication(self, tokens):
        """Parse multiplication, division, and modulo"""
        left = self._parse_exponentiation(tokens)

        while tokens and tokens[0] in ("*", "/", "//", "%"):
            op = tokens.pop(0)
            right = self._parse_exponentiation(tokens)

            left_val = left.value
            right_val = right.value
            result = self.operators[op](left_val, right_val)

            # Combine roll details
            combined_rolls = left.rolls + right.rolls
            combined_expression = f"{left.expression} {op} {right.expression}"

            left = RollResult(result, combined_rolls, combined_expression)

        return left

    def _parse_exponentiation(self, tokens):
        """Parse exponentiation"""
        left = self._parse_primary(tokens)

        if tokens and tokens[0] == "^":
            tokens.pop(0)  # Remove the ^ operator
            right = self._parse_exponentiation(tokens)  # Right-associative

            result = self.operators["^"](left.value, right.value)

            # Combine roll details
            combined_rolls = left.rolls + right.rolls
            combined_expression = f"{left.expression} ^ {right.expression}"

            return RollResult(result, combined_rolls, combined_expression)

        return left

    def _parse_primary(self, tokens):
        """Parse primary expressions (numbers, dice rolls, parentheses)"""
        if not tokens:
            return RollResult(0, [], "")

        token = tokens.pop(0)

        # Handle parenthesized expressions
        if token == "(":
            result = self._evaluate_expression(tokens)

            if tokens and tokens[0] == ")":
                tokens.pop(0)  # Remove the closing parenthesis
            else:
                raise ValueError("Mismatched parentheses")

            return RollResult(
                result.value, result.rolls, f"({result.expression})"
            )

        # Handle dice rolls
        dice_match = self.dice_pattern.match(token)
        if dice_match:
            return self._roll_dice(dice_match)

        # Handle numbers
        try:
            value = float(token)
            if value.is_integer():
                value = int(value)
            return RollResult(value, [], str(value))
        except ValueError:
            raise ValueError(f"Unexpected token: {token}")

    def _roll_dice(self, dice_match):
        """Roll dice based on the dice notation"""
        count_str, sides_str = dice_match.groups()

        # Handle the # notation for multiple separate dice rolls
        if "#" in count_str:
            count = int(count_str.split("#")[0])
            separate_rolls = True
        else:
            count = int(count_str)
            separate_rolls = False

        sides = int(sides_str)

        if sides <= 0 or count < 0:
            raise ValueError("Invalid dice specification")

        # Roll the dice
        rolls = []
        for _ in range(count):
            roll = random.randint(1, sides)
            rolls.append(roll)

        # Calculate the result value
        total = sum(rolls)

        # Format the roll details
        roll_text = f"{count}d{sides}"

        # For separate roll handling (like the example with 2#d6+2)
        if separate_rolls:
            roll_text = (
                f"{count}#d{sides}"  # Preserve the # notation in the result
            )

        return RollResult(total, [(rolls, roll_text)], str(total))

    def roll(self, expression):
        """Roll dice and evaluate the expression, with formatted output"""
        try:
            result = self.parse(expression)
            return self._format_result(result, expression)
        except Exception as e:
            return f"Error: {str(e)}"

    def _format_result(self, result, original_expression):
        """Format the result like in the provided example"""
        output_lines = []

        # For handling multiple separate dice rolls (#)
        if "#" in original_expression:
            dice_matches = re.findall(r"(\d+)#d(\d+)", original_expression)

            # Process each #d pattern
            for count_str, sides_str in dice_matches:
                count = int(count_str)
                sides = int(sides_str)

                # Replace the #d syntax with regular dice for evaluation
                modified_expr = re.sub(
                    f"{count}#d{sides}",
                    f"1d{sides}",
                    original_expression,
                    count=1,
                )

                # Perform multiple separate rolls
                for i in range(count):
                    single_roll_result = self.parse(modified_expr)

                    # Extract the dice roll result
                    for rolls, notation in single_roll_result.rolls:
                        if (
                            "d" + sides_str in notation
                        ):  # Find the specific dice we're interested in
                            roll_value = rolls[
                                0
                            ]  # Only one die per roll in this case

                            # Bold formatting for max rolls
                            if roll_value == sides:
                                roll_str = f"[**{roll_value}**]"
                            else:
                                roll_str = f"[{roll_value}]"

                            # Get the rest of the expression by removing the dice part
                            rest_of_expr = modified_expr.replace(
                                f"1d{sides}", ""
                            ).strip()

                            # Format the output based on whether there's additional math
                            if rest_of_expr:
                                output_lines.append(
                                    f"` {single_roll_result.value} ` ⟵ {roll_str} 1d{sides} {rest_of_expr}"
                                )
                            else:
                                output_lines.append(
                                    f"` {single_roll_result.value} ` ⟵ {roll_str} 1d{sides}"
                                )
                            break

                # Add total line if multiple rolls
                if count > 1:
                    total_value = sum(
                        self.parse(modified_expr).value for _ in range(count)
                    )
                    output_lines.append(f" Total: {total_value}")

        else:
            # Regular single evaluation with proper formatting
            if not result.rolls:
                # For pure math expressions without dice
                output_lines.append(
                    f"` {result.value} ` ⟵ {original_expression}"
                )
                return "\n".join(output_lines)

            # Map dice notations to their formatted results
            dice_map = {}
            for rolls, notation in result.rolls:
                # Format rolls with bold for max values
                formatted_roll_values = []
                sides = int(notation.split("d")[1]) if "d" in notation else 0

                for roll in rolls:
                    if roll == sides:
                        formatted_roll_values.append(f"**{roll}**")
                    else:
                        formatted_roll_values.append(str(roll))

                roll_str = f"[{', '.join(formatted_roll_values)}] {notation}"
                dice_map[notation] = roll_str

            # Format the expression by replacing dice notations with their results
            formatted_expr = original_expression

            # Sort dice notations by length (descending) to avoid partial replacements
            dice_notations = sorted(dice_map.keys(), key=len, reverse=True)

            # Replace each dice notation with its formatted result
            for dice in dice_notations:
                # Only replace complete dice notations (not partial matches)
                pattern = re.compile(r"\b" + re.escape(dice) + r"\b")
                formatted_expr = pattern.sub(dice_map[dice], formatted_expr)

            # Replace math operators with spaces around them for better readability
            for op in self.operators.keys():
                if op in formatted_expr:
                    formatted_expr = formatted_expr.replace(op, f" {op} ")

            # Clean up extra spaces
            formatted_expr = re.sub(r"\s+", " ", formatted_expr).strip()

            # For expressions with parentheses, maintain them
            formatted_expr = formatted_expr.replace("( ", "(").replace(
                " )", ")"
            )

            output_lines.append(f"` {result.value} ` ⟵ {formatted_expr}")

        return "\n".join(output_lines)


# Example usage
if __name__ == "__main__":
    parser = DiceParser()

    # Example from the prompt
    print(parser.roll("2#d6+2"))
    print("---")

    # Additional examples
    print(parser.roll("3d6 + 4"))
    print(parser.roll("(1d20 + 5) * 2"))
    print(parser.roll("2d4 + 3d6 - 1 + 4 * 0"))
    print(parser.roll("1d100 // 10"))
    print(parser.roll("5 + 3 * 2"))  # Pure math test
    print(parser.roll("(7-2) ^ 2"))  # Testing exponentiation

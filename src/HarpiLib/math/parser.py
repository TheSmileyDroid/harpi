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
        self.dice_pattern = re.compile(r"(\d+#?)d(\d+)")
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
        if count_str.endswith("#"):
            count = int(count_str[:-1])  # Remove the # from the end
            separate_rolls = True
            original_notation = f"{count_str}d{sides_str}"
        else:
            count = int(count_str)
            separate_rolls = False
            original_notation = f"{count_str}d{sides_str}"

        sides = int(sides_str)

        if sides <= 0 or count < 0:
            raise ValueError("Invalid dice specification")

        # Roll the dice
        rolls = []
        for _ in range(count):
            roll = random.randint(1, sides)
            rolls.append(roll)

        # For separate rolls (#), return max value instead of sum
        if separate_rolls:
            # For separate rolls, the value should be the maximum of all rolls
            max_value = max(rolls)
            return RollResult(
                max_value, [(rolls, original_notation)], original_notation
            )
        else:
            # Calculate the result value normally
            total = sum(rolls)
            return RollResult(total, [(rolls, original_notation)], str(total))

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
            # Extract the dice notation and additional math
            dice_match = re.search(r"(\d+)#d(\d+)", original_expression)
            if dice_match:
                count = int(dice_match.group(1))
                sides = int(dice_match.group(2))

                # Get additional math after the dice
                rest_of_expr = original_expression[dice_match.end() :].strip()

                # Get the actual rolls from the result
                for rolls, notation in result.rolls:
                    if "#" in notation:
                        individual_rolls = rolls

                        # Show each individual roll
                        for roll_value in individual_rolls:
                            # Bold formatting for max rolls
                            if roll_value == sides:
                                roll_str = f"[**{roll_value}**]"
                            else:
                                roll_str = f"[{roll_value}]"

                            # Calculate final value for this roll
                            if rest_of_expr:
                                # Simple math evaluation
                                try:
                                    final_value = eval(
                                        f"{roll_value}{rest_of_expr}"
                                    )
                                    output_lines.append(
                                        f"` {final_value} ` ⟵ {roll_str} 1d{sides} {rest_of_expr}"
                                    )
                                except Exception:
                                    final_value = roll_value
                                    output_lines.append(
                                        f"` {final_value} ` ⟵ {roll_str} 1d{sides}"
                                    )
                            else:
                                output_lines.append(
                                    f"` {roll_value} ` ⟵ {roll_str} 1d{sides}"
                                )

                        # Add max value if multiple rolls
                        if count > 1:
                            max_roll = max(individual_rolls)
                            if rest_of_expr:
                                try:
                                    max_value = eval(
                                        f"{max_roll}{rest_of_expr}"
                                    )
                                except Exception:
                                    max_value = max_roll
                            else:
                                max_value = max_roll
                            output_lines.append(f"Max: {max_value}")
                        break
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

    # Debug test
    print("=== DEBUG TEST ===")
    roll_result = parser.parse("2#d6")
    print(f"Value: {roll_result.value}")
    print(f"Rolls: {roll_result.rolls}")
    print(f"Expression: {roll_result.expression}")
    print("==================")

    # Example from the prompt
    print(parser.roll("2#d6+2"))
    print("---")

    roll_result = parser.parse("2#d6")
    print(parser._format_result(roll_result, "2#d6"))
    print(roll_result.value)  # Should print the max of the two rolls
    print("---")

    # Additional examples
    print(parser.roll("3d6 + 4"))
    print(parser.roll("(1d20 + 5) * 2"))
    print(parser.roll("2d4 + 3d6 - 1 + 4 * 0"))
    print(parser.roll("1d100 // 10"))
    print(parser.roll("5 + 3 * 2"))  # Pure math test
    print(parser.roll("(7-2) ^ 2"))  # Testing exponentiation

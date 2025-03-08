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
            roll_text = f"1d{sides}"

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
            dice_match = re.search(r"(\d+)#d(\d+)", original_expression)
            if dice_match:
                count = int(dice_match.group(1))
                sides = int(dice_match.group(2))

                # Replace the #d syntax with regular dice for evaluation
                modified_expr = original_expression.replace(
                    f"{count}#d{sides}", f"1d{sides}"
                )

                # Perform multiple separate rolls
                for i in range(count):
                    roll_result = self.parse(modified_expr)
                    roll_details = ""

                    for rolls, notation in roll_result.rolls:
                        roll_value = rolls[
                            0
                        ]  # Only one die per roll in this case
                        # Bold formatting for max rolls
                        if roll_value == sides:
                            roll_str = f"[**{roll_value}**]"
                        else:
                            roll_str = f"[{roll_value}]"
                        roll_details += f"{roll_str} {notation}"

                    # Add the rest of the expression
                    full_details = f"{roll_details} {modified_expr.replace('1d' + str(sides), '')}"
                    output_lines.append(
                        f"` {roll_result.value} ` ⟵ {full_details.strip()}"
                    )
        else:
            # Regular single evaluation
            roll_details = ""
            for rolls, notation in result.rolls:
                roll_str = f"[{', '.join(str(r) for r in rolls)}]"
                roll_details += f"{roll_str} {notation} "

            output_lines.append(
                f"` {result.value} ` ⟵ {roll_details}{original_expression}"
            )

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
    print(parser.roll("2d4 + 3d6 - 1"))
    print(parser.roll("1d100 // 10"))

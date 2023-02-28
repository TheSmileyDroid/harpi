import re
import random

dice = '3d6-3d4'
pattern = r'\d+[d]\d+|\+|\-|\d+'
dice = dice.lower().replace(' ', '')
matches: list = re.findall(pattern, dice)
print(matches)

result = 0
result_string = ''


def roll_dice(dice_string):
    print(dice_string)
    parts = dice_string.split('d')
    count = int(parts[0])
    sides = int(parts[1])
    rolls = [random.randint(1, sides) for _ in range(count)]
    return rolls, sum(rolls)


operator = '+'
for match in matches:
    match: str = match
    if match == '+':
        operator = '+'
        result_string += '+ '
    elif match == '-':
        operator = '-'
        result_string += '- '
    elif match.isnumeric():
        result += int(match) * (1 if operator == '+' else -1)
        result_string += f'{match} '
    elif 'd' in match:
        result_dice, result_ = roll_dice(match)
        result += result_ * (1 if operator == '+' else -1)
        result_string += f'{result_dice}{match} '
    else:
        print('Error: invalid match')


print(f'{result} = {result_string}')

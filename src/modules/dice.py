import random
from discord.ext import commands
import re
import logging as log


def roll_dice(dice_string):
    print(dice_string)
    parts = dice_string.split('d')
    count = int(parts[0]) if parts[0] != '' else 1
    sides = int(parts[1]) if parts[1] != '' else 6
    rolls = [random.randint(1, sides) for _ in range(count)]
    return rolls, sum(rolls)


class Dice(commands.Cog):

    @commands.command(name='d', aliases=['dado', 'rolar', 'roll', 'r'])
    async def roll(self, ctx, *, dice: str):
        if '#' in dice:
            count = int(dice.split('#')[0])
            dice = dice.split('#')[1]
            rolls = []

            for _ in range(count):
                roll = self.roll_multiple(ctx, dice)
                rolls.append(roll)

            result_text = ''
            for roll in rolls:
                result_text += f'{roll}\n'

            await ctx.send(f'{ctx.author.mention}\n{result_text}')
        else:
            await self.roll_simple(ctx, dice)

    async def roll_simple(self, ctx, dice):
        pattern = r'\d+[d]\d+|\+|\-|\d+'
        dice = dice.lower().replace(' ', '')
        matches: list = re.findall(pattern, dice)
        log.info(matches)

        result = 0
        result_string = ''

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

        log.info(f'{result} = {result_string}')

        await ctx.send(f'{ctx.author.mention} {result} = {result_string}')

    def roll_multiple(self, ctx, dice):
        pattern = r'\d+[d]\d+|\+|\-|\d+'
        dice = dice.lower().replace(' ', '')
        matches: list = re.findall(pattern, dice)
        log.info(matches)

        result = 0
        result_string = ''

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

        log.info(f'{result} = {result_string}')

        return f'{result} = {result_string}'


async def setup(bot):
    await bot.add_cog(Dice(bot))

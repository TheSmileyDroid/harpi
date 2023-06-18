import json

from src.modules.utils import aiassist
from discord.ext import commands


def get_valid_list(response: str) -> list[str]:
    valid_list: list[str] = []
    # Checa se a string da lista pode ser convertida para uma lista de string em python
    try:
        valid_list = json.loads(response)
    except ValueError:
        raise ValueError("Invalid list")
    if type(valid_list) != list:
        raise ValueError("Invalid list")
    for arg in valid_list:
        if type(arg) != str:
            raise ValueError("Invalid list")
    if len(valid_list) == 0:
        raise ValueError("Invalid list")
    return valid_list


class CommandRunner:
    def __init__(self):
        self.temp = 0.2
        self.top_p = 0.1
        self.parent_id = ''
        self.system = ''
        f = open('src/modules/utils/command_runner.txt', 'r')
        for line in f:
            self.system += line
        f.close()

    async def run_command(self,
                          ctx: commands.Context,
                          prompt: str) -> str:
        async with ctx.typing():
            res = self.get_response(prompt)

            arglist = get_valid_list(res)

            command = arglist[0]

            cmd: commands.Command = ctx.bot.get_command(command)

            args = ' '.join(arglist[1:])

            try:
                await ctx.invoke(cmd, args=args)
            except TypeError:
                try:
                    await ctx.invoke(cmd)
                except TypeError:
                    raise commands.errors.CommandNotFound

        return res

    def get_response(self, prompt: str) -> str:
        return self.get_response_aiassist(prompt)

    def get_response_aiassist(self, prompt: str) -> str:
        req = aiassist.Completion.create(
            prompt=prompt,
            systemMessage=self.system,
            parentMessageId=self.parent_id,
            temperature=self.temp,
            top_p=self.top_p,
        )
        self.parent_id = req["parentMessageId"]
        return req["text"]

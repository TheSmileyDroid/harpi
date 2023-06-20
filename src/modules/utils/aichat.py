from src.modules.utils import aiassist
from discord.ext import commands
from src.modules.utils.bots.command_runner import CommandRunner
from src.modules.utils.bots.searcher import Searcher


class AIChat:
    def __init__(self):
        self.command_runner = CommandRunner()
        self.searcher = Searcher()
        self.chat_mem = []
        self.parent_id = ''
        self.temp = 0.8
        self.top_p = 0.8
        self.system = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            self.system += line
        f.close()
        self.reset()

    def reset(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.parent_id = ''
        self.system = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            self.system += line
        f.close()
        self.chat_mem.append({'role': 'system', 'content': self.system})

    async def chat(self,
                   ctx: commands.Context,
                   prompt: str) -> str:
        prompt_with_author = ctx.author.name + ": " + prompt

        info = await self.searcher.call(ctx, prompt)

        if info == '{NOQUERY}':
            info = ''
        else:
            info += '\n\n'

        res = self.get_response(info + prompt_with_author)

        try:
            await self.check_commands(ctx, res, self.command_runner)
        except Exception as e:
            print(e)
            await ctx.send("**Error running command**")

        return res

    async def check_commands(self, ctx, response: str, command_runner: CommandRunner):
        text = response
        if '-[' in text and ']-' in text:
            runnable_commands = []
            there_is_a_command = True
            while there_is_a_command:
                runnable_commands.append(
                    text[text.find('-[') + 2:text.find(']-')])
                text = text[text.find(']-') + 2:]
                if '-[' not in text or ']-' not in text:
                    there_is_a_command = False
            for command in runnable_commands:
                await self.command_runner.call(ctx, command)

    def set_temp(self, temp: float):
        if temp < 0.1 or temp > 0.9:
            raise ValueError("Temperature must be between 0.1 and 0.9")
        self.temp = temp

    def set_top_p(self, top_p: float):
        if top_p < 0.1 or top_p > 0.9:
            raise ValueError("Top P must be between 0.1 and 0.9")
        self.top_p = top_p

    def get_temp(self) -> float:
        return self.temp

    def get_top_p(self) -> float:
        return self.top_p

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

    def get_response(self, prompt: str) -> str:
        return self.get_response_aiassist(prompt)

    def clear(self):
        self.reset()

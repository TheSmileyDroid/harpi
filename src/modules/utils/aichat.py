from src.modules.utils import aiassist
from typing import Optional
from discord.ext import commands
from src.modules.utils.bots.command_runner import CommandRunner
from src.modules.utils.bots.searcher import Searcher
import time

from src.modules.utils.send import Message


class AIChat:
    def __init__(self):
        self.command_runner = CommandRunner()
        self.searcher = Searcher()
        self.chat_mem = []
        self.parent_id = ''
        self.temp = 0.8
        self.top_p = 0.8
        self.system = 'Data atual: ' + time.strftime('%d/%m/%Y') + '\n'
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

    async def search(self,
                     ctx: commands.Context | None,
                     prompt: str) -> str:
        if ctx is not None:
            prompt_with_author = ctx.author.name + ": " + prompt
        else:
            prompt_with_author = 'smileydroid' + ": " + prompt

        info = ''

        try:

            info = await self.searcher.call(ctx, '"' + prompt + '"')

            if info == 'NOQUERY':
                info = ''
            else:
                info += '\n\n'
        except Exception as e:
            print(e)
            info = '\n\n'

        print(info + prompt_with_author)

        res = await self.get_response(info + prompt_with_author, ctx)

        try:
            await self.check_commands(ctx, res)
            if ctx is None:
                return res
        except Exception as e:
            print(e)
            if ctx is None:
                return res
            await ctx.send("**Error running command**")

        return res

    async def chat(self,
                   ctx: commands.Context | None,
                   prompt: str) -> str:
        if ctx is not None:
            prompt_with_author = ctx.author.name + ": " + prompt
        else:
            prompt_with_author = 'smileydroid' + ": " + prompt

        print(prompt_with_author)

        res = await self.get_response(prompt_with_author, ctx)

        return res

    async def check_commands(self, ctx: commands.Context | None, response: str):
        text = response
        if '{' in text and '}' in text:
            runnable_commands = []
            there_is_a_command = True
            while there_is_a_command:
                start = text.find('{')
                end = text.find('}')
                if start == -1 or end == -1:
                    there_is_a_command = False
                    continue
                command = text[start + 1:end]
                runnable_commands.append(command)
                text = text[end + 1:]
            for command in runnable_commands:
                print(command)
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

    async def get_response_aiassist(self, prompt: str, ctx: commands.Context | None = None) -> str:
        req = await aiassist.Completion.create(
            prompt=prompt,
            systemMessage=self.system,
            parentMessageId=self.parent_id,
            temperature=self.temp,
            top_p=self.top_p,
            ctx=ctx
        )
        self.parent_id = req["parentMessageId"]
        print(req["text"])
        return req["text"]

    async def get_response(self, prompt: str, ctx: Optional[commands.Context] = None) -> str:
        if ctx is None:
            raise Exception("Desculpe, o sistema de chat está desativado no momento.")
        return await Message(ctx, "Desculpe, o sistema de chat está desativado no momento.").send()

    def clear(self):
        self.reset()

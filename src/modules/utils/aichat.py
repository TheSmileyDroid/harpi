import os
from src.modules.utils import aiassist
from discord.ext import commands


class AIChat:
    def __init__(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.parent_id = None
        self.temp = 0.8
        self.top_p = 0.8
        self.poe_token = os.environ.get('POE_TOKEN')
        self.system = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            self.system += line
        f.close()
        self.reset()

    def reset(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.parent_id = None
        self.system = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            self.system += line
        f.close()
        self.chat_mem.append({'role': 'system', 'content': self.system})

    def chat(self,
             ctx: commands.Context,
             prompt: str) -> str:
        prompt = ctx.author.name + ": " + prompt
        res = self.get_response(prompt)

        return res

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

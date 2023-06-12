import os
from src.modules.utils import aiassist
from discord.ext import commands
import src.modules.utils.g4f as g4f


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
        self.temp = temp

    def set_top_p(self, top_p: float):
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

    def get_response_g4f(self, prompt: str) -> str:
        self.chat_mem.append({'role': 'user', 'content': prompt})
        response = g4f.ChatCompletion.create(model='gpt-3.5-turbo',
                                             messages=self.chat_mem)
        self.chat_mem.append({'role': 'system', 'content': response})
        return response

    def get_response(self, prompt: str) -> str:
        return self.get_response_g4f(prompt)

    def clear(self):
        self.reset()

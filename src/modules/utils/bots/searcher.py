from src.modules.utils import aiassist
from discord.ext import commands
import wikipedia  # type: ignore


class Searcher:
    def __init__(self):
        self.temp = 0.1
        self.top_p = 0.1
        self.parent_id = ''
        self.querytranslator = ''
        f = open('src/modules/utils/querytranslator.txt', 'r')
        for line in f:
            self.querytranslator += line
        f.close()
        wikipedia.set_lang('pt')

    async def call(self,
                   ctx: commands.Context | None,
                   prompt: str) -> str:
        query = self.get_response(prompt, self.querytranslator)

        print(query)

        if query == 'NOQUERY':
            return 'NOQUERY'

        if ctx is not None:
            await ctx.send("Procurando por: " + query)

        itens = wikipedia.search(query)

        if len(itens) == 0:
            return 'NOQUERY'

        result = wikipedia.summary(itens[0], sentences=10)

        return '{' + result + '}'

    def get_response(self, prompt: str, system: str) -> str:
        return self.get_response_aiassist(prompt, system)

    def get_response_aiassist(self, prompt: str, system: str) -> str:
        req = aiassist.Completion.create(
            prompt=prompt,
            systemMessage=system,
            parentMessageId=self.parent_id,
            temperature=self.temp,
            top_p=self.top_p,
        )
        self.parent_id = ''
        return req["text"]

from src.modules.utils import aiassist
from src.modules.utils.bots.googlesearch import GoogleSearch
from discord.ext import commands


class Searcher:
    def __init__(self):
        self.temp = 0.4
        self.top_p = 0.2
        self.parent_id = ''
        self.querytranslator = ''
        f = open('src/modules/utils/querytranslator.txt', 'r')
        for line in f:
            self.querytranslator += line
        f.close()
        self.textinterpreter = ''
        f = open('src/modules/utils/textinterpreter.txt', 'r')
        for line in f:
            self.textinterpreter += line
        f.close()
        self.searchengine = GoogleSearch()

    async def call(self,
                   ctx: commands.Context,
                   prompt: str) -> str:

        async with ctx.typing():
            query = self.get_response(prompt, self.querytranslator)

            if query == 'NOQUERY':
                return 'NOQUERY'

            await ctx.send("Procurando por: " + query)

            itens = self.searchengine.search(query=query)

            itens_str = ''
            for result in itens:
                itens_str += "Link: " + result['link'] + "\n"
                itens_str += "Title: " + result['title'] + "\n"
                itens_str += "Content: " + result['snippet'] + "\n\n"

            itens_str = "{" + prompt + "}" + itens_str

            info = self.get_response(itens_str, self.textinterpreter)

            return '{' + info + '}'

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

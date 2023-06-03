from src.modules.utils.aternos import Aternos
from discord.ext import commands


class Minecraft(commands.Cog):
    aternos = Aternos()

    @commands.command(name='mc')
    async def mc(self, ctx: commands.Context):
        """Mostra o status do servidor de Minecraft."""
        try:
            server = self.aternos.list_servers()[0]
            server.fetch()
            await ctx.send(
                f"O servidor {server.subdomain} está {server.status}")
        except Exception as e:
            await ctx.send(
                f"Erro ao executar o comando: {e}")

    @commands.command(name='mcstart')
    async def mcstart(self, ctx: commands.Context):
        """Inicia o servidor de Minecraft."""
        try:
            server = self.aternos.list_servers()[0]
            server.fetch()
            server.start()
            await ctx.send(
                f"O servidor {server.subdomain} está {server.status}")
        except Exception as e:
            await ctx.send(
                f"Erro ao executar o comando: {e}")

    @commands.command(name='mcservers')
    async def mcservers(self, ctx: commands.Context):
        """Mostra os servidores de Minecraft."""
        try:
            servers = self.aternos.list_servers()
            result = ""
            for server in servers:
                server.fetch()
                result += f"{server.domain} "
            await ctx.send(f"Servidores: {result}")
        except Exception as e:
            await ctx.send(f"Erro ao executar o comando: {e}")

    @commands.command(name='mclistplayers')
    async def mclistplayers(self, ctx: commands.Context):
        """Lista os jogadores do servidor de Minecraft."""
        try:
            server = self.aternos.list_servers()[0]
            server.fetch()
            players = server.players_list
            result = ""
            for player in players:
                result += f"{player} "
            await ctx.send(f"Jogadores: {result}")
        except Exception as e:
            await ctx.send(f"Erro ao executar o comando: {e}")


async def setup(bot):
    await bot.add_cog(Minecraft(bot))

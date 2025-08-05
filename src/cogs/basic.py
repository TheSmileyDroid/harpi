"""Basic COG."""

import asyncio
import io
import re
import subprocess
from datetime import datetime

import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from discord.ext.commands.bot import Bot
import psutil
from discord import Embed, File
from discord.ext import commands
from mcstatus import JavaServer

from src.cogs.base import TrackedCog


class BasicCog(TrackedCog):
    """Basic bot commands like ping, echo, and system status."""

    @commands.command()
    async def ping(self, ctx: commands.Context[Bot]) -> None:
        """Responde Ping de volta."""
        await ctx.send("Pong!")

    @commands.command()
    async def echo(self, ctx: commands.Context[Bot], *, args: str) -> None:
        """Repete a mensagem."""
        await ctx.send(args)

    @commands.command()
    async def status(self, ctx: commands.Context[Bot]) -> None:
        """Mostra o estado do servidor."""

        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        uptime = psutil.boot_time()
        uptime = int(uptime)
        uptime = datetime.fromtimestamp(  # noqa: DTZ006
            uptime,
        )
        uptime = datetime.now() - uptime
        uptime = str(uptime).split(".")[0]
        uptime = re.sub(
            r"(\d+):(\d+):(\d+)",
            r"\1 horas, \2 minutos e \3 segundos",
            uptime,
        )
        space = psutil.disk_usage("/")
        external_disk = psutil.disk_usage("/home/opc/external")

        embed = Embed(
            title="Status do Harpi",
            description="Aqui estão as informações do servidor.",
            color=0x22DD77,
        )
        embed.add_field(name="Uso de CPU", value=f"{cpu}%")
        embed.add_field(name="Uso de Memória", value=f"{memory.percent}%")
        embed.add_field(name="Uptime", value=uptime)
        embed.add_field(
            name="Espaço em Disco",
            value=f"{space.percent}% ({space.used / 1024**3:.2f} GB usados de {space.total / 1024**3:.2f} GB)",
        )
        embed.add_field(
            name="Disco Externo",
            value=f"{external_disk.percent}% ({external_disk.used / 1024**3:.2f} GB usados de {external_disk.total / 1024**3:.2f} GB)",
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def mc(self, ctx: commands.Context[Bot]) -> None:
        """Mostra o status do servidor Minecraft."""
        java_process = [
            process
            for process in psutil.process_iter(attrs=["pid", "name"])
            if "java" in process.info["name"]
        ]
        if not java_process:
            await ctx.send("O servidor de Minecraft não está rodando.")
            return
        server = JavaServer.lookup("localhost:25565")
        status = server.status()
        cpu = java_process[0].cpu_percent(interval=1)
        memory = java_process[0].memory_info().rss / 1024**2
        embed = Embed(
            title="Status do servidor de Minecraft",
            color=0x11CC99,
        )
        embed.add_field(name="Versão", value=status.version.name)
        embed.add_field(name="Jogadores", value=str(status.players.online))
        embed.add_field(name="Uso de CPU", value=f"{cpu}%")
        embed.add_field(name="Uso de Memória", value=f"{memory:.2f} MB")
        players_sample = status.players.sample
        if players_sample:
            players_list = "\n".join([
                player.name for player in players_sample
            ])
        else:
            players_list = "Ninguém está jogando."
        embed.add_field(
            name="Lista de Jogadores",
            value=players_list,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def top(self, ctx: commands.Context[Bot]) -> None:
        """Retorna o retorno do comando top como uma imagem."""

        result = await asyncio.to_thread(
            subprocess.check_output,
            ["top", "-b", "-n", "1"],
        )
        result = result.decode("utf-8")

        # Limitar o número de linhas para um tamanho razoável
        lines = result.split("\n")[:20]  # Limitando a 20 linhas

        # Configurações da imagem
        font_size = 14
        padding = 20
        line_height = font_size + 4

        try:
            # Tentar usar uma fonte monoespaçada (melhor para output de terminal)
            font = PIL.ImageFont.truetype("DejaVuSansMono.ttf", font_size)
        except OSError:
            try:
                # Tentar alternativa comum
                font = PIL.ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                    font_size,
                )
            except OSError:
                font = PIL.ImageFont.load_default()

        # Criar imagem temporária para calcular dimensões de texto
        temp_img = PIL.Image.new("RGB", (1, 1), color=(0, 0, 0))
        draw = PIL.ImageDraw.Draw(temp_img)

        # Calcular largura máxima necessária
        max_width = 0
        for line in lines:
            try:
                # Para PIL >= 9.2.0
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
            except AttributeError:
                # Fallback para versões anteriores
                width = len(line) * (font_size // 2)
            max_width = max(max_width, width)

        # Configurar dimensões da imagem
        img_width = min(
            max_width + padding * 2,
            1000,
        )  # Limitar largura máxima
        img_height = len(lines) * line_height + padding * 2

        # Criar imagem com esquema de cores agradável
        bg_color = (25, 25, 35)  # Fundo escuro azulado
        image = PIL.Image.new(
            "RGB",
            (int(img_width), int(img_height)),
            color=bg_color,
        )
        draw = PIL.ImageDraw.Draw(image)

        # Adicionar título
        title = "Status do Servidor - Monitor de Processos"
        draw.text(
            (padding, padding // 2),
            title,
            font=font,
            fill=(135, 206, 250),
        )

        # Desenhar linhas com esquema de cores para legibilidade
        y_pos = padding + line_height

        for i, line in enumerate(lines):
            if i == 0:  # Cabeçalho principal
                color = (0, 255, 127)  # Verde claro
            elif i <= 2:  # Estatísticas do sistema
                color = (102, 204, 255)  # Azul claro
            elif i <= 6:  # Cabeçalhos e informações
                color = (255, 165, 0)  # Laranja
            else:  # Processos
                color = (220, 220, 220)  # Cinza claro

            draw.text((padding, y_pos), line, font=font, fill=color)
            y_pos += line_height

        # Adicionar bordas e sombras
        draw.rectangle(
            [(0, 0), (img_width - 1, img_height - 1)],
            outline=(80, 80, 120),
            width=2,
        )

        # Salvar para um buffer
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        # Enviar com uma mensagem descritiva
        await ctx.send(
            "📊 **Informações do Sistema:**",
            file=File(buffer, filename="top_command.png"),
        )

    @commands.command()
    async def shutdown(self, ctx: commands.Context[Bot]) -> None:
        """Desliga o Harpi."""
        await ctx.send("Desligando...")
        await ctx.bot.close()

import asyncio
import io
import re
import subprocess
from datetime import datetime

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import psutil
from discord import Embed, File
from discord.ext import commands


_MONO_FONT_CANDIDATES = (
    "DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)


def _load_mono_font(
    font_size: int,
) -> PIL.ImageFont.FreeTypeFont | PIL.ImageFont.ImageFont:
    for candidate in _MONO_FONT_CANDIDATES:
        try:
            return PIL.ImageFont.truetype(candidate, font_size)
        except OSError:
            continue
    return PIL.ImageFont.load_default()


def _text_width(
    draw: PIL.ImageDraw.ImageDraw,
    line: str,
    font: PIL.ImageFont.FreeTypeFont | PIL.ImageFont.ImageFont,
    font_size: int,
) -> int:
    try:
        # For PIL >= 9.2.0
        bbox = draw.textbbox((0, 0), line, font=font)
        return int(bbox[2] - bbox[0])
    except AttributeError:
        # Fallback for older versions
        return len(line) * (font_size // 2)


def _line_color(index: int) -> tuple[int, int, int]:
    if index == 0:  # Main header
        return (0, 255, 127)  # Light green
    if index <= 2:  # System statistics
        return (102, 204, 255)  # Light blue
    if index <= 6:  # Headers and info
        return (255, 165, 0)  # Orange
    return (220, 220, 220)  # Processes


def _render_top_image(output: str) -> io.BytesIO:
    lines = output.split("\n")[:20]

    font_size = 14
    padding = 20
    line_height = font_size + 4
    font = _load_mono_font(font_size)

    measure_img = PIL.Image.new("RGB", (1, 1), color=(0, 0, 0))
    measure_draw = PIL.ImageDraw.Draw(measure_img)
    max_width = max(
        _text_width(measure_draw, line, font, font_size) for line in lines
    )

    img_width = min(
        max_width + padding * 2,
        1000,
    )
    img_height = len(lines) * line_height + padding * 2

    image = PIL.Image.new(
        "RGB",
        (round(img_width), round(img_height)),
        color=(25, 25, 35),  # Dark bluish background
    )
    draw = PIL.ImageDraw.Draw(image)

    title = "Status do Servidor - Monitor de Processos"
    draw.text(
        (padding, padding // 2),
        title,
        font=font,
        fill=(135, 206, 250),
    )

    y_pos = padding + line_height

    for i, line in enumerate(lines):
        draw.text((padding, y_pos), line, font=font, fill=_line_color(i))
        y_pos += line_height

    draw.rectangle(
        [(0, 0), (img_width - 1, img_height - 1)],
        outline=(80, 80, 120),
        width=2,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class GeneralCog(commands.Cog):
    """General-purpose Discord commands (ping, echo, status, shutdown)."""

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        """Reply with Pong."""
        await ctx.send("Pong!")

    @commands.command()
    async def echo(self, ctx: commands.Context, *, args: str) -> None:
        """Echo a message back."""
        await ctx.send(args)

    @commands.command()
    async def status(self, ctx: commands.Context) -> None:
        """Show server status."""

        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        uptime = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(uptime)
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
    async def top(self, ctx: commands.Context) -> None:
        """Return the top command output as an image."""

        result = await asyncio.to_thread(
            subprocess.check_output,
            ["top", "-b", "-n", "1"],
        )
        if isinstance(result, bytes):
            result = result.decode("utf-8")

        buffer = await asyncio.to_thread(_render_top_image, result)

        await ctx.send(
            "📊 **Informações do Sistema:**",
            file=File(buffer, filename="top_command.png"),
        )

    @commands.command()
    async def shutdown(self, ctx: commands.Context) -> None:
        """Shut down the Harpi bot."""
        await ctx.send("Desligando...")
        await ctx.bot.close()

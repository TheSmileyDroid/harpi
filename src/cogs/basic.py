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
import psutil
from discord import Embed, File
from discord.ext import commands


class BasicCog(commands.Cog):
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
    async def top(self, ctx: commands.Context) -> None:
        """Return the top command output as an image."""

        result = await asyncio.to_thread(
            subprocess.check_output,
            ["top", "-b", "-n", "1"],  # type: ignore
        )
        result = result.decode("utf-8")

        # Limit the number of lines to a reasonable size
        lines = result.split("\n")[:20]  # Limit to 20 lines

        # Image settings
        font_size = 14
        padding = 20
        line_height = font_size + 4

        try:
            # Try to use a monospaced font (better for terminal output)
            font = PIL.ImageFont.truetype("DejaVuSansMono.ttf", font_size)
        except OSError:
            try:
                # Try common alternative
                font = PIL.ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                    font_size,
                )
            except OSError:
                font = PIL.ImageFont.load_default()

        # Create temporary image to calculate text dimensions
        temp_img = PIL.Image.new("RGB", (1, 1), color=(0, 0, 0))
        draw = PIL.ImageDraw.Draw(temp_img)

        # Calculate maximum required width
        max_width = 0
        for line in lines:
            try:
                # For PIL >= 9.2.0
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
            except AttributeError:
                # Fallback for older versions
                width = len(line) * (font_size // 2)
            max_width = max(max_width, width)

        # Set image dimensions
        img_width = min(
            max_width + padding * 2,
            1000,
        )  # Limit maximum width
        img_height = len(lines) * line_height + padding * 2

        # Create image with a pleasant color scheme
        bg_color = (25, 25, 35)  # Dark bluish background
        image = PIL.Image.new(
            "RGB",
            (int(img_width), int(img_height)),
            color=bg_color,
        )
        draw = PIL.ImageDraw.Draw(image)

        # Add title
        title = "Status do Servidor - Monitor de Processos"
        draw.text(
            (padding, padding // 2),
            title,
            font=font,
            fill=(135, 206, 250),
        )

        # Draw lines with color scheme for readability
        y_pos = padding + line_height

        for i, line in enumerate(lines):
            if i == 0:  # Main header
                color = (0, 255, 127)  # Light green
            elif i <= 2:  # System statistics
                color = (102, 204, 255)  # Light blue
            elif i <= 6:  # Headers and info
                color = (255, 165, 0)  # Orange
            else:  # Processes
                color = (220, 220, 220)  # Light gray

            draw.text((padding, y_pos), line, font=font, fill=color)
            y_pos += line_height

        # Add borders and shadows
        draw.rectangle(
            [(0, 0), (img_width - 1, img_height - 1)],
            outline=(80, 80, 120),
            width=2,
        )

        # Save to a buffer
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        # Send with a descriptive message
        await ctx.send(
            "📊 **Informações do Sistema:**",
            file=File(buffer, filename="top_command.png"),
        )

    @commands.command()
    async def shutdown(self, ctx: commands.Context) -> None:
        """Shut down the Harpi bot."""
        await ctx.send("Desligando...")
        await ctx.bot.close()

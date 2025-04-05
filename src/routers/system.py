"""Router para informações de sistema e status do servidor."""

from __future__ import annotations

import asyncio
import io
import re
import subprocess
from datetime import datetime
from typing import List, Optional

import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import psutil
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from mcstatus import JavaServer
except ImportError:
    JavaServer = None  # type: ignore

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


class DiskInfo(BaseModel):
    """Informações de um disco."""

    path: str
    total: float
    used: float
    free: float
    percent: float


class SystemStatus(BaseModel):
    """Status do sistema com informações de recursos."""

    cpu_percent: float = Field(..., description="Percentual de uso de CPU")
    memory_percent: float = Field(
        ..., description="Percentual de uso de memória"
    )
    memory_total: float = Field(..., description="Total de memória em GB")
    memory_used: float = Field(..., description="Memória usada em GB")
    uptime: str = Field(..., description="Tempo de atividade do sistema")
    disks: List[DiskInfo] = Field(..., description="Informações de discos")


class MinecraftPlayer(BaseModel):
    """Informações de um jogador de Minecraft."""

    name: str
    id: Optional[str] = None


class MinecraftStatus(BaseModel):
    """Status do servidor Minecraft."""

    is_running: bool = Field(..., description="Se o servidor está rodando")
    version: Optional[str] = None
    online_players: Optional[int] = None
    max_players: Optional[int] = None
    players_list: List[MinecraftPlayer] = []
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None


class ProcessInfo(BaseModel):
    """Informações de um processo do sistema."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    command: str


class TopProcesses(BaseModel):
    """Lista dos processos mais ativos do sistema."""

    timestamp: str = Field(..., description="Timestamp da coleta")
    processes: List[ProcessInfo] = Field(..., description="Lista de processos")


@router.get("/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """Obtém o status atual do sistema.

    Retorna informações sobre CPU, memória, discos e uptime.

    Returns
    -------
    SystemStatus
        Objeto contendo estatísticas do sistema.
    """
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)

    # Calcular uptime
    uptime_seconds = psutil.boot_time()
    uptime_seconds = int(uptime_seconds)
    uptime_datetime = datetime.fromtimestamp(uptime_seconds)
    uptime_delta = datetime.now() - uptime_datetime
    uptime_str = str(uptime_delta).split(".")[0]
    uptime_formatted = re.sub(
        r"(\d+):(\d+):(\d+)",
        r"\1 horas, \2 minutos e \3 segundos",
        uptime_str,
    )

    # Informações dos discos
    disks_info = []

    # Disco principal
    root_disk = psutil.disk_usage("/")
    disks_info.append(
        DiskInfo(
            path="/",
            total=root_disk.total / (1024**3),
            used=root_disk.used / (1024**3),
            free=root_disk.free / (1024**3),
            percent=root_disk.percent,
        )
    )

    # Verificar se existe o disco externo mencionado no BasicCog
    try:
        external_disk = psutil.disk_usage("/home/opc/external")
        disks_info.append(
            DiskInfo(
                path="/home/opc/external",
                total=external_disk.total / (1024**3),
                used=external_disk.used / (1024**3),
                free=external_disk.free / (1024**3),
                percent=external_disk.percent,
            )
        )
    except (FileNotFoundError, PermissionError):
        # Disco externo não existe ou não tem permissão
        pass

    return SystemStatus(
        cpu_percent=cpu,
        memory_percent=memory.percent,
        memory_total=memory.total / (1024**3),
        memory_used=memory.used / (1024**3),
        uptime=uptime_formatted,
        disks=disks_info,
    )


@router.get("/minecraft", response_model=MinecraftStatus)
async def get_minecraft_status() -> MinecraftStatus:
    """Obtém o status do servidor Minecraft.

    Verifica se o servidor está rodando e obtém informações como
    versão, jogadores online e uso de recursos.

    Returns
    -------
    MinecraftStatus
        Status do servidor Minecraft.
    """
    # Verificar se há um processo Java rodando
    java_processes = [
        process
        for process in psutil.process_iter(attrs=["pid", "name"])
        if "java" in process.info["name"]
    ]

    if not java_processes or not JavaServer:
        # Servidor não está rodando ou módulo mcstatus não está disponível
        return MinecraftStatus(is_running=False)

    try:
        server = JavaServer.lookup("localhost:25565")
        status = server.status()

        cpu = java_processes[0].cpu_percent(interval=1)
        memory = java_processes[0].memory_info().rss / (1024**2)

        players_list = []
        if status.players.sample:
            players_list = [
                MinecraftPlayer(name=player.name, id=str(player.id))
                for player in status.players.sample
            ]

        return MinecraftStatus(
            is_running=True,
            version=status.version.name,
            online_players=status.players.online,
            max_players=status.players.max,
            players_list=players_list,
            cpu_percent=cpu,
            memory_mb=memory,
        )
    except Exception:
        # Falha ao conectar ao servidor
        return MinecraftStatus(is_running=True)


@router.get("/top", response_model=TopProcesses)
async def get_top_processes() -> TopProcesses:
    """Obtém informações sobre os processos mais ativos do sistema.

    Similar ao comando 'top' do Linux, retorna uma lista dos processos
    que estão consumindo mais recursos.

    Returns
    -------
    TopProcesses
        Lista dos processos mais ativos.
    """
    processes = []

    # Obter os 15 processos com maior uso de CPU
    for proc in sorted(
        psutil.process_iter([
            "pid",
            "name",
            "cmdline",
            "cpu_percent",
            "memory_percent",
        ]),
        key=lambda p: p.info["cpu_percent"],
        reverse=True,
    )[:15]:
        try:
            cmd = (
                " ".join(proc.info["cmdline"])
                if proc.info["cmdline"]
                else "[kernel]"
            )
            processes.append(
                ProcessInfo(
                    pid=proc.info["pid"],
                    name=proc.info["name"],
                    cpu_percent=proc.info["cpu_percent"],
                    memory_percent=proc.info["memory_percent"],
                    command=cmd[:100],  # Limitar tamanho do comando
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Processo pode ter terminado ou não temos acesso
            continue

    return TopProcesses(
        timestamp=datetime.now().isoformat(),
        processes=processes,
    )


@router.get("/top/image")
async def get_top_image() -> Response:
    """Retorna uma imagem com a saída do comando 'top'.

    Gera uma imagem contendo a saída formatada do comando 'top',
    semelhante ao que é feito no comando do Discord.

    Returns
    -------
    StreamingResponse
        Imagem PNG contendo a saída do 'top'.
    """
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

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=top_output.png"},
    )

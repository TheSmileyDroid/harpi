import asyncio
import os
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

PY = sys.executable
SERVER = str(Path(__file__).with_name("sse_server.py"))
CLK = os.sysconf("SC_CLK_TCK")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def cpu_seconds(pid):
    with open(f"/proc/{pid}/stat") as f:
        parts = f.read().split()
    return (int(parts[13]) + int(parts[14])) / CLK


def rss_kb(pid):
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return 0


def start(port):
    proc = subprocess.Popen(
        [PY, SERVER, str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.2):
                return proc
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("server did not start")


async def read_headers(reader):
    raw = await reader.readuntil(b"\r\n\r\n")
    headers = {}
    for line in raw.split(b"\r\n")[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            headers[k.strip().lower()] = v.strip()
    return raw, headers


async def sse_client(port, path, seconds, out):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    req = (
        f"GET {path}?seconds={seconds} HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        "Accept: text/event-stream\r\nConnection: close\r\n\r\n"
    ).encode()
    writer.write(req)
    await writer.drain()
    total = len(req)
    frames = 0
    while True:
        chunk = await reader.read(65536)
        if not chunk:
            break
        total += len(chunk)
        frames += chunk.count(b"event: table")
    writer.close()
    out.append((total, frames))


async def poll_client(port, hz, seconds, out):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    sent = recv = requests = 0
    interval = 1.0 / hz
    while loop.time() < end:
        started = loop.time()
        req = f"GET /poll HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode()
        writer.write(req)
        await writer.drain()
        sent += len(req)
        header, headers = await read_headers(reader)
        length = int(headers.get(b"content-length", b"0"))
        body = await reader.readexactly(length)
        recv += len(header) + len(body)
        requests += 1
        await asyncio.sleep(max(0.0, started + interval - loop.time()))
    writer.close()
    out.append((sent, recv, requests))


async def move_client(port, hz, seconds, out):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    sent = recv = requests = 0
    interval = 1.0 / hz
    while loop.time() < end:
        started = loop.time()
        body = b'{"id":"token-3","x":341.75,"y":412.0}'
        req = (
            f"POST /move HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
        ).encode() + body
        writer.write(req)
        await writer.drain()
        sent += len(req)
        header, headers = await read_headers(reader)
        length = int(headers.get(b"content-length", b"0"))
        payload = await reader.readexactly(length)
        recv += len(header) + len(payload)
        requests += 1
        await asyncio.sleep(max(0.0, started + interval - loop.time()))
    writer.close()
    out.append((sent, recv, requests))


async def idle_client(port, seconds, out):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(
        (
            f"GET /idle?seconds={seconds} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
        ).encode()
    )
    await writer.drain()
    out.append((reader, writer))


async def gather(kind, port, clients, seconds, hz):
    out = []
    if kind == "sse":
        tasks = [
            asyncio.create_task(sse_client(port, "/sse", seconds, out))
            for _ in range(clients)
        ]
    elif kind == "sse_full":
        tasks = [
            asyncio.create_task(sse_client(port, "/sse_full", seconds, out))
            for _ in range(clients)
        ]
    elif kind == "poll":
        tasks = [
            asyncio.create_task(poll_client(port, hz, seconds, out))
            for _ in range(clients)
        ]
    elif kind == "move":
        tasks = [
            asyncio.create_task(move_client(port, hz, seconds, out))
            for _ in range(clients)
        ]
    elif kind == "idle":
        tasks = [
            asyncio.create_task(idle_client(port, seconds, out))
            for _ in range(clients)
        ]
    await asyncio.gather(*tasks)
    return out


def bench(kind, clients, hz=None, seconds=8, runs=3):
    rows = []
    for _ in range(runs):
        port = free_port()
        proc = start(port)
        try:
            time.sleep(0.7)
            base_cpu = cpu_seconds(proc.pid)
            out = asyncio.run(gather(kind, port, clients, seconds, hz))
            cpu = cpu_seconds(proc.pid) - base_cpu
            if kind in ("sse", "sse_full"):
                total = sum(x[0] for x in out)
                n = sum(x[1] for x in out)
            else:
                total = sum(x[0] + x[1] for x in out)
                n = sum(x[2] for x in out)
            rows.append((total, cpu, n))
        finally:
            proc.terminate()
            proc.wait(timeout=5)
    total = statistics.median(r[0] for r in rows)
    cpu = statistics.median(r[1] for r in rows)
    n = statistics.median(r[2] for r in rows)
    unit = "frame" if kind.startswith("sse") else "req"
    print(
        f"{kind:8s} clients={clients:2d} hz={hz or 0:>2} : {n:.0f} {unit}s, "
        f"{total/1024:7.1f} KiB, {total/seconds/1024:6.2f} KiB/s, "
        f"CPU {cpu*1000:4.0f} ms ({cpu/seconds*100:5.2f}% core), "
        f"{cpu/n*1e6 if n else 0:6.1f} us/{unit}, "
        f"{total/n if n else 0:6.0f} B/{unit}"
    )


def bench_idle(clients=64, seconds=12):
    port = free_port()
    proc = start(port)
    try:
        time.sleep(0.5)
        base = rss_kb(proc.pid)
        hold = asyncio.run(gather("idle", port, clients, seconds, None))
        time.sleep(1.5)
        after = rss_kb(proc.pid)
        print(
            f"idle     connections={clients}: RSS {base} KiB -> {after} KiB, "
            f"{(after-base)*1024/clients:.0f} B/connection"
        )
        try:
            for _, writer in hold:
                writer.close()
        except RuntimeError:
            pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "sse"):
        bench("sse", 8)
        bench("sse", 32)
        bench("sse_full", 8)
    if which in ("all", "poll"):
        bench("poll", 8, hz=10)
        bench("poll", 8, hz=1)
        bench("move", 1, hz=10)
        bench("move", 8, hz=10)
    if which in ("all", "idle"):
        bench_idle()

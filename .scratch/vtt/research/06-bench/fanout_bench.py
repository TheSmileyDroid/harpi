import asyncio
import os
import socket
import statistics
from pathlib import Path
import subprocess
import sys
import time

PY = sys.executable
SERVER = str(Path(__file__).with_name("fanout_server.py"))
CLK = os.sysconf("SC_CLK_TCK")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def cpu_seconds(pid):
    with open(f"/proc/{pid}/stat") as f:
        parts = f.read().split()
    return (int(parts[13]) + int(parts[14])) / CLK


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


async def sse_reader(port, seconds, out):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(
        (
            f"GET /table/sse HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            "Accept: text/event-stream\r\nConnection: close\r\n\r\n"
        ).encode()
    )
    await writer.drain()
    total = frames = 0
    end = asyncio.get_running_loop().time() + seconds
    while asyncio.get_running_loop().time() < end:
        try:
            chunk = await asyncio.wait_for(reader.read(65536), 0.5)
        except TimeoutError:
            continue
        if not chunk:
            break
        total += len(chunk)
        frames += chunk.count(b"event: table")
    writer.close()
    out.append((total, frames))


async def mover(port, hz, seconds, out, token):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    sent = recv = 0
    n = 0
    interval = 1.0 / hz
    while loop.time() < end:
        started = loop.time()
        body = (
            '{"id":"%s","x":%.2f,"y":%.2f}' % (token, 100 + n, 200 + n)
        ).encode()
        req = (
            f"POST /table/move HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
        ).encode() + body
        writer.write(req)
        await writer.drain()
        sent += len(req)
        header, headers = await read_headers(reader)
        length = int(headers.get(b"content-length", b"0"))
        payload = await reader.readexactly(length)
        recv += len(header) + len(payload)
        n += 1
        await asyncio.sleep(max(0.0, started + interval - loop.time()))
    writer.close()
    out.append((sent, recv, n))


async def run(port, readers, movers, hz, seconds):
    out = []
    tasks = [asyncio.create_task(sse_reader(port, seconds, out)) for _ in range(readers)]
    move_out = []
    tasks += [
        asyncio.create_task(
            mover(port, hz, seconds, move_out, f"01J8ZP4M7Q9R2S5T8V0W3X6Y{i:02d}")
        )
        for i in range(movers)
    ]
    await asyncio.gather(*tasks)
    return out, move_out


def bench(readers, movers, hz=10, seconds=8, runs=3):
    rows = []
    for _ in range(runs):
        port = free_port()
        proc = start(port)
        try:
            time.sleep(0.7)
            base = cpu_seconds(proc.pid)
            sse_out, move_out = asyncio.run(run(port, readers, movers, hz, seconds))
            cpu = cpu_seconds(proc.pid) - base
            frames = sum(f for _, f in sse_out)
            bytes_out = sum(b for b, _ in sse_out) + sum(m[0] + m[1] for m in move_out)
            posts = sum(m[2] for m in move_out)
            rows.append((frames, posts, bytes_out, cpu))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
    frames, posts, total, cpu = (statistics.median(r[i] for r in rows) for i in range(4))
    print(
        f"readers={readers} movers={movers}@{hz}Hz: {frames:.0f} frames, {posts:.0f} posts, "
        f"{total/1024:.1f} KiB, {total/seconds/1024:.2f} KiB/s, "
        f"CPU {cpu*1000:.0f} ms ({cpu/seconds*100:.2f}% core)"
    )


if __name__ == "__main__":
    bench(8, 0)
    bench(8, 1)
    bench(8, 8)
    bench(32, 8)

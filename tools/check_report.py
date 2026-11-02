"""Runs the `make check` gates and prints one consolidated report.

Every gate writes its own log under `.check/logs/`, so the Python and web
lanes stop shredding each other's lines. The summary carries the verdict and
the numbers; the detail section carries only what failed, capped.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / ".check"
LOGS = CHECK / "logs"
REPORTS = CHECK / "reports"
BASELINE = ROOT / ".jscpd-baseline.json"
VITEST_SUMMARY = ROOT / "web" / "coverage" / "coverage-summary.json"

DETAIL_LIMIT = 10
TAIL_LINES = 20
FINGERPRINT_LENGTH = 16
LANE_PARALLELISM = 3

JSCPD_COMMAND = (
    "bunx jscpd@3.5.10 src/ pages/ web/src/ "
    '--ignore "**/lib/contract/**,**/*.test.ts" --min-tokens 50 '
    "--reporters json,console --output .check/reports/jscpd"
)

Parser = Callable[[str, Path], tuple[str, list["Finding"]]]


@dataclass(frozen=True)
class Finding:
    where: str
    message: str

    def line(self) -> str:
        if not self.where:
            return self.message
        return f"{self.where}  {self.message}"


@dataclass(frozen=True)
class Gate:
    name: str
    lane: str
    command: str
    parse: Parser
    cwd: Path = ROOT
    fails_on_findings: bool = False
    tail: bool = False


@dataclass
class Result:
    gate: Gate
    code: int
    seconds: float
    summary: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        if self.code != 0:
            return False
        return not (self.gate.fails_on_findings and self.findings)

    @property
    def log(self) -> Path:
        return LOGS / f"{self.gate.name}.log"


def findings_of(
    pattern: re.Pattern[str],
    log: str,
    template: str,
    message: str = "{msg}",
) -> list[Finding]:
    found: list[Finding] = []
    for match in pattern.finditer(log):
        groups = match.groupdict()
        found.append(
            Finding(template.format(**groups), message.format(**groups))
        )
    return found


RUFF = re.compile(
    r"^(?P<path>[^:\s]+):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<code>\S+) (?P<msg>.*)$",
    re.MULTILINE,
)
TY = re.compile(
    r"^(?P<path>[^:\s]+):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<code>error|warning)\[(?P<rule>[^\]]+)\] (?P<msg>.*)$",
    re.MULTILINE,
)
VULTURE = re.compile(
    r"^(?P<path>[^:\s]+):(?P<line>\d+): (?P<msg>.*) \(\d+% confidence\)$",
    re.MULTILINE,
)
CRAP = re.compile(
    r"^(?P<path>[^:\s]+):(?P<line>\d+) (?P<name>\S+) (?P<msg>CRAP=.*)$",
    re.MULTILINE,
)
PRETTIER = re.compile(r"^\[warn\] (?P<path>\S+)$", re.MULTILINE)
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def parse_ruff(log: str, _: Path) -> tuple[str, list[Finding]]:
    found = findings_of(RUFF, log, "{path}:{line}", "{code} {msg}")
    return plural(len(found), "issue"), found


def parse_ty(log: str, _: Path) -> tuple[str, list[Finding]]:
    found = findings_of(TY, log, "{path}:{line}")
    return plural(len(found), "error"), found


def parse_vulture(log: str, _: Path) -> tuple[str, list[Finding]]:
    found = findings_of(VULTURE, log, "{path}:{line}")
    return plural(len(found), "dead name"), found


def parse_crap(log: str, _: Path) -> tuple[str, list[Finding]]:
    found = findings_of(CRAP, log, "{path}:{line} {name}")
    return plural(len(found), "function over CRAP 8"), found


def plural(count: int, noun: str) -> str:
    if count == 0:
        return "clean"
    return counted(count, noun)


def counted(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def parse_ruff_format(log: str, _: Path) -> tuple[str, list[Finding]]:
    would = [
        Finding(path, "would reformat")
        for path in re.findall(r"^Would reformat: (.+)$", log, re.MULTILINE)
    ]
    if would:
        return f"{len(would)} file(s) would reformat", would
    match = re.search(r"(\d+) files? already formatted", log)
    if match:
        return f"{match.group(1)} files formatted", []
    return "clean", []


def parse_prettier(log: str, _: Path) -> tuple[str, list[Finding]]:
    found = [
        Finding(match.group("path"), "not formatted")
        for match in PRETTIER.finditer(log)
    ]
    if found:
        return f"{len(found)} file(s) not formatted", found
    if "All matched files use Prettier code style" in log:
        return "clean", []
    return "clean", []


def parse_contract_diff(log: str, _: Path) -> tuple[str, list[Finding]]:
    paths = [line.split("\t")[-1] for line in log.splitlines() if line]
    if not paths:
        return "no diff", []
    return f"{len(paths)} generated file(s) differ", [
        Finding(path, "regenerate with make contract") for path in paths
    ]


def parse_pytest(log: str, reports: Path) -> tuple[str, list[Finding]]:
    summary = pytest_summary(log)
    report = reports / "pytest.xml"
    if not report.is_file():
        return summary, []
    root = ElementTree.parse(report).getroot()
    return summary, list(pytest_failures(root))


def pytest_failures(suite: ElementTree.Element) -> Iterator[Finding]:
    for case in suite.iter("testcase"):
        for child in case:
            if child.tag not in ("failure", "error"):
                continue
            classname = case.get("classname", "")
            where = f"{classname.replace('.', '/')}.py::{case.get('name')}"
            message = (child.get("message") or "").strip().splitlines()
            yield Finding(where, message[0] if message else child.tag)


def pytest_summary(log: str) -> str:
    match = re.search(r"^(\d+) passed", log, re.MULTILINE)
    parts: list[str] = []
    if match:
        parts.append(f"{match.group(1)} passed")
    for label in ("failed", "error", "errors", "skipped", "xfailed"):
        hit = re.search(rf"(\d+) {label}\b", log)
        if hit:
            parts.append(f"{hit.group(1)} {label}")
    coverage = re.search(r"Total coverage: (\d+\.\d+)%", log)
    if coverage:
        parts.append(f"coverage {coverage.group(1)}%")
    return " · ".join(parts) if parts else "no result line"


def parse_svelte(log: str, _: Path) -> tuple[str, list[Finding]]:
    found: list[Finding] = []
    for block in re.finditer(
        r"^(?P<path>/\S+?):(?P<line>\d+):(?P<col>\d+)\n"
        r"(?P<level>Error|Warn|Hint): (?P<msg>.*) \((?P<source>\w+)\)$",
        log,
        re.MULTILINE,
    ):
        grouping = block.groupdict()
        found.append(
            Finding(f"{grouping['path']}:{grouping['line']}", grouping["msg"])
        )
    match = re.search(
        r"svelte-check found (\d+) errors? and (\d+) warnings?", log
    )
    if match:
        return (
            f"{counted(int(match.group(1)), 'error')} · "
            f"{counted(int(match.group(2)), 'warning')}",
            found,
        )
    return ("no result line", found)


def parse_eslint(_log: str, reports: Path) -> tuple[str, list[Finding]]:
    report = reports / "eslint.json"
    if not report.is_file():
        return "no report", []
    found: list[Finding] = []
    for entry in json.loads(report.read_text(encoding="utf-8")):
        for message in entry.get("messages", []):
            rule = message.get("ruleId") or "fatal"
            found.append(
                Finding(
                    f"{entry['filePath']}:{message.get('line', 0)}",
                    f"{rule} {message.get('message', '')}",
                )
            )
    return plural(len(found), "problem"), found


def parse_knip(_log: str, reports: Path) -> tuple[str, list[Finding]]:
    report = reports / "knip.json"
    if not report.is_file():
        return "no report", []
    found: list[Finding] = []
    for row in json.loads(report.read_text(encoding="utf-8")).get(
        "issues", []
    ):
        path = row.get("file", "")
        for kind, entries in row.items():
            if kind in ("file", "owners") or not isinstance(entries, list):
                continue
            for entry in entries:
                name = entry.get("name") or entry.get("symbol") or ""
                line = entry.get("line") or 0
                found.append(Finding(f"{path}:{line}", f"{kind} {name}"))
    return plural(len(found), "issue"), found


def parse_vitest(log: str, _reports: Path) -> tuple[str, list[Finding]]:
    tests = re.search(r"Tests\s+(\d+) passed", log)
    summary = f"{tests.group(1)} passed" if tests else "no result line"
    if "Coverage report" not in log or not VITEST_SUMMARY.is_file():
        return summary, []
    totals = json.loads(VITEST_SUMMARY.read_text(encoding="utf-8"))
    percent = totals.get("total", {}).get("lines", {}).get("pct")
    if percent is not None:
        summary = f"{summary} · lines {percent}%"
    return summary, []


def clone_fingerprint(fragment: str) -> str:
    normalized = "\n".join(
        line.strip() for line in fragment.splitlines() if line.strip()
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:FINGERPRINT_LENGTH]


def jscpd_clones(reports: Path) -> list[dict]:
    report = reports / "jscpd" / "jscpd-report.json"
    if not report.is_file():
        return []
    return json.loads(report.read_text(encoding="utf-8")).get("duplicates", [])


def clone_where(clone: dict) -> str:
    first = clone["firstFile"]
    second = clone["secondFile"]
    return (
        f"{first['name']}:{first['start']} ↔ "
        f"{second['name']}:{second['start']}"
    )


def accepted_fingerprints() -> set[str]:
    if not BASELINE.is_file():
        return set()
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    return {
        entry["fingerprint"]
        for entry in document.get("accept", [])
        if str(entry.get("reason", "")).strip()
    }


def parse_jscpd(_log: str, reports: Path) -> tuple[str, list[Finding]]:
    clones = jscpd_clones(reports)
    accepted = accepted_fingerprints()
    new: list[Finding] = []
    for clone in clones:
        fingerprint = clone_fingerprint(clone.get("fragment", ""))
        if fingerprint in accepted:
            continue
        label = f"{clone_where(clone)}"
        new.append(
            Finding(
                label,
                f"{clone['lines']} lines · new clone {fingerprint}",
            )
        )
    known = len(clones) - len(new)
    summary = f"{len(clones)} clones · {known} known · {len(new)} new"
    return summary, new


def gates(fast: bool) -> list[Gate]:
    return [
        Gate(
            name="contract",
            lane="py",
            command="git diff --name-status -- web/src/lib/contract",
            parse=parse_contract_diff,
            fails_on_findings=True,
        ),
        Gate(
            name="ruff",
            lane="py",
            command=(
                "uv run ruff check --output-format concise --color never "
                "src/ pages/ app.py tools/ tests/"
            ),
            parse=parse_ruff,
        ),
        Gate(
            name="ruff-format",
            lane="py",
            command=(
                "uv run ruff format --check --color never "
                "src/ pages/ app.py tools/ tests/"
            ),
            parse=parse_ruff_format,
        ),
        Gate(
            name="ty",
            lane="py",
            command=(
                "uv run ty check --output-format concise "
                "src/ tests/ pages/ app.py tools/"
            ),
            parse=parse_ty,
        ),
        Gate(
            name="pytest",
            lane="py",
            command=pytest_command(fast),
            parse=parse_pytest,
            tail=True,
        ),
        Gate(
            name="crap",
            lane="py",
            command="uv run python tools/crap_check.py coverage.json",
            parse=parse_crap,
        ),
        Gate(
            name="vulture",
            lane="py",
            command="uv run vulture",
            parse=parse_vulture,
        ),
        Gate(
            name="jscpd",
            lane="web",
            command=JSCPD_COMMAND,
            parse=parse_jscpd,
            fails_on_findings=True,
        ),
        Gate(
            name="eslint",
            lane="web",
            command=(
                "bunx eslint src e2e --format json "
                f"--output-file {REPORTS / 'eslint.json'}"
            ),
            parse=parse_eslint,
            cwd=ROOT / "web",
        ),
        Gate(
            name="prettier",
            lane="web",
            command="bun run format:check",
            parse=parse_prettier,
            cwd=ROOT / "web",
        ),
        Gate(
            name="svelte-check",
            lane="web",
            command="bun run typecheck",
            parse=parse_svelte,
            cwd=ROOT / "web",
            tail=True,
        ),
        Gate(
            name="vitest",
            lane="web",
            command="bun run test" if fast else "bun run test:coverage",
            parse=parse_vitest,
            cwd=ROOT / "web",
            tail=True,
        ),
        Gate(
            name="knip",
            lane="web",
            command=(
                "bunx knip --reporter symbols --reporter json "
                f"--output-file json={REPORTS / 'knip.json'}"
            ),
            parse=parse_knip,
            cwd=ROOT / "web",
            tail=True,
        ),
    ]


def pytest_command(fast: bool) -> str:
    coverage = (
        ""
        if fast
        else (
            "--cov=src --cov=pages --cov=app --cov-report=json "
            "--cov-fail-under=70 "
        )
    )
    return (
        f"uv run pytest tests/ {coverage}--tb=short -q -n auto "
        "--dist worksteal --junitxml=.check/reports/pytest.xml"
    )


def is_skipped(gate: Gate, fast: bool) -> bool:
    return fast and gate.name in (
        "contract",
        "crap",
        "vulture",
        "jscpd",
        "knip",
    )


async def run_gate(gate: Gate) -> Result:
    started = time.monotonic()
    log_path = LOGS / f"{gate.name}.log"
    with log_path.open("w", encoding="utf-8") as sink:
        process = await asyncio.create_subprocess_shell(
            gate.command,
            cwd=gate.cwd,
            stdout=sink,
            stderr=asyncio.subprocess.STDOUT,
            env=no_color_env(),
        )
        code = await process.wait()
    seconds = time.monotonic() - started
    text = log_path.read_text(encoding="utf-8", errors="replace")
    summary, findings = read_output(gate, text)
    return Result(gate, code, seconds, summary, findings)


def read_output(gate: Gate, text: str) -> tuple[str, list[Finding]]:
    try:
        return gate.parse(text, REPORTS)
    except (ValueError, KeyError, TypeError, ElementTree.ParseError) as error:
        return f"could not read output: {error}", []


def no_color_env() -> dict[str, str]:
    return {**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0"}


async def run_sequential(gates: Sequence[Gate]) -> list[Result]:
    return [await run_gate(gate) for gate in gates]


async def run_parallel(gates: Sequence[Gate]) -> list[Result]:
    limit = asyncio.Semaphore(LANE_PARALLELISM)

    async def limited(gate: Gate) -> Result:
        async with limit:
            return await run_gate(gate)

    return list(await asyncio.gather(*(limited(gate) for gate in gates)))


async def run_all(gates: Sequence[Gate]) -> list[Result]:
    python_lane = [gate for gate in gates if gate.lane == "py"]
    web_lane = [gate for gate in gates if gate.lane == "web"]
    python_results, web_results = await asyncio.gather(
        run_sequential(python_lane), run_parallel(web_lane)
    )
    return [*python_results, *web_results]


def render(
    results: Sequence[Result], elapsed: float, full: bool, label: str
) -> str:
    failed = [result for result in results if not result.ok]
    head = (
        f"{label} · {counted(len(results), 'gate')} · "
        f"{len(failed)} failed · {elapsed:.0f}s"
    )
    lines = [head]
    if failed:
        names = ", ".join(result.gate.name for result in failed)
        lines.append(f"FAILED: {names}")
    lines.append("")
    width = max(len(result.gate.name) for result in results)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        lines.append(
            f"{status}  {result.gate.name:<{width}}  "
            f"{result.seconds:4.1f}s  {result.summary}"
        )
    lines.append("")
    lines.append(
        "logs: .check/logs  ·  --full for raw output  ·  "
        "--only <gate> to rerun"
    )
    for result in failed:
        lines.extend(["", *render_failure(result, full)])
    return "\n".join(lines)


def render_failure(result: Result, full: bool) -> list[str]:
    lines = [f"{result.gate.name} · FAIL"]
    shown = result.findings if full else result.findings[:DETAIL_LIMIT]
    lines.extend(f"  {finding.line()}" for finding in shown)
    hidden = len(result.findings) - len(shown)
    if hidden > 0:
        lines.append(f"  ... {hidden} more (--full)")
    if result.gate.tail or not result.findings:
        lines.append(f"  log: {result.log.relative_to(ROOT)}")
        lines.extend(f"  | {line}" for line in tail(result.log, full))
    return lines


def tail(log: Path, full: bool) -> list[str]:
    text = log.read_text(encoding="utf-8", errors="replace")
    lines = ANSI.sub("", text).rstrip().splitlines()
    if full:
        return lines
    return lines[-TAIL_LINES:]


def select(args: argparse.Namespace) -> list[Gate]:
    available = [
        gate for gate in gates(args.fast) if not is_skipped(gate, args.fast)
    ]
    if not args.only:
        return available
    wanted = [name.strip() for name in args.only.split(",") if name.strip()]
    unknown = set(wanted) - {gate.name for gate in available}
    if unknown:
        raise SystemExit(f"unknown gate(s): {', '.join(sorted(unknown))}")
    return [gate for gate in available if gate.name in wanted]


def prepare_reports(clean: bool = True) -> None:
    for directory in (LOGS, REPORTS):
        directory.mkdir(parents=True, exist_ok=True)
    if clean:
        for stale in REPORTS.iterdir():
            if stale.is_dir():
                shutil.rmtree(stale)
            else:
                stale.unlink()


def run(args: argparse.Namespace) -> int:
    prepare_reports()
    selected = select(args)
    started = time.monotonic()
    results = asyncio.run(run_all(selected))
    elapsed = time.monotonic() - started
    label = "make check-fast" if args.fast else "make check"
    print(render(results, elapsed, args.full, label))
    return 0 if all(result.ok for result in results) else 1


def accept(fingerprint: str, reason: str) -> int:
    prepare_reports(clean=False)
    matches = [
        clone
        for clone in jscpd_clones(REPORTS)
        if clone_fingerprint(clone.get("fragment", "")).startswith(fingerprint)
    ]
    if not matches:
        print(
            "no clone with that fingerprint in .check/reports/jscpd; "
            "run `uv run python tools/check_report.py --only jscpd` first",
            file=sys.stderr,
        )
        return 2
    if not reason.strip():
        print("a reason is required to accept a clone", file=sys.stderr)
        return 2
    document: dict[str, Any] = (
        json.loads(BASELINE.read_text(encoding="utf-8"))
        if BASELINE.is_file()
        else {"version": 1, "accept": []}
    )
    entries: dict[str, Any] = {
        entry["fingerprint"]: entry for entry in document.get("accept", [])
    }
    for clone in matches:
        key = clone_fingerprint(clone.get("fragment", ""))
        entries[key] = {
            "fingerprint": key,
            "lines": clone["lines"],
            "where": clone_where(clone),
            "reason": reason.strip(),
        }
    document["accept"] = sorted(
        entries.values(), key=lambda entry: entry["fingerprint"]
    )
    BASELINE.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for clone in matches:
        print(f"accepted {clone_where(clone)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check_report.py")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="skip the contract diff, coverage, CRAP, vulture, jscpd and knip",
    )
    parser.add_argument(
        "--only", default="", help="comma separated gate names"
    )
    parser.add_argument("--full", action="store_true", help="show everything")
    commands = parser.add_subparsers(dest="command")
    accept_parser = commands.add_parser("accept")
    accept_parser.add_argument("fingerprint")
    accept_parser.add_argument("--reason", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "accept":
        return accept(args.fingerprint, args.reason)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

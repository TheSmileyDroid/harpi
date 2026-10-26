"""Pure decisions behind deploy/release-gate.sh, unit tested off the network."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"
STATUSES = frozenset({PASS, FAIL, SKIP})

PUBLIC_HOSTNAME = "harpi.smileydroid.com.br"
EXPECTED_OPEN_PORTS = frozenset({80, 443})
COOKIE_PREFIX = "__Host-"
HSTS_HEADER = "strict-transport-security"
NMAP_PORT_LINE = re.compile(
    r"^\s*(?P<port>\d+)/(?:tcp|udp)\s+(?P<state>[a-z|]+)\b"
)
HSTS_MAX_AGE = re.compile(r"max-age\s*=\s*(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str

    def line(self) -> str:
        return f"{self.status} {self.name}: {self.detail}"


def passed(name: str, detail: str) -> Check:
    return Check(name, PASS, detail)


def failed(name: str, detail: str) -> Check:
    return Check(name, FAIL, detail)


def skipped(name: str, detail: str) -> Check:
    return Check(name, SKIP, detail)


def cookie_name(set_cookie: str) -> str:
    first = set_cookie.split(";", 1)[0]
    return first.split("=", 1)[0].strip()


def cookie_attributes(set_cookie: str) -> tuple[str, ...]:
    parts = [part.strip() for part in set_cookie.split(";")]
    return tuple(part for part in parts[1:] if part)


def cookie_problems(name: str, attributes: set[str]) -> list[str]:
    problems: list[str] = []
    if not name.startswith(COOKIE_PREFIX):
        problems.append(
            f"name {name or '(empty)'} has no {COOKIE_PREFIX} prefix"
        )
    for attribute, label in (("secure", "Secure"), ("httponly", "HttpOnly")):
        if attribute not in attributes:
            problems.append(f"missing {label}")
    if "samesite=lax" not in attributes:
        problems.append("SameSite is not Lax")
    if "path=/" not in attributes:
        problems.append("Path is not /")
    if any(attribute.startswith("domain=") for attribute in attributes):
        problems.append("has a Domain attribute")
    return problems


def check_login_cookie(set_cookie: str) -> Check:
    if not set_cookie.strip():
        return failed(
            "login cookie", "the login response carries no Set-Cookie"
        )
    name = cookie_name(set_cookie)
    attributes = {
        attribute.lower() for attribute in cookie_attributes(set_cookie)
    }
    problems = cookie_problems(name, attributes)
    if problems:
        return failed("login cookie", ", ".join(problems))
    return passed(
        "login cookie",
        f"{name} carries Secure, HttpOnly, SameSite=Lax, Path=/",
    )


def header_value(headers: str, name: str) -> str:
    for line in headers.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == name.lower():
            return value.strip()
    return ""


def check_hsts(headers: str) -> Check:
    value = header_value(headers, HSTS_HEADER)
    if not value:
        return failed("hsts", "no Strict-Transport-Security header")
    match = HSTS_MAX_AGE.search(value)
    if match is None:
        return failed("hsts", f"{value} has no max-age")
    if int(match.group(1)) <= 0:
        return failed("hsts", f"{value} disables HSTS with max-age=0")
    if "includesubdomains" in value.lower():
        return failed("hsts", f"{value} includes subdomains")
    return passed("hsts", value)


def check_status(name: str, actual: str, expected: int) -> Check:
    code = actual.strip() or "000"
    if code == str(expected):
        return passed(name, f"answered {code}")
    return failed(name, f"answered {code}, expected {expected}")


def dns_addresses(answer: str) -> tuple[str, ...]:
    lines = (line.strip() for line in answer.splitlines() if line.strip())
    return tuple(dict.fromkeys(lines))


def check_no_dns(answer: str, hostname: str = PUBLIC_HOSTNAME) -> Check:
    addresses = dns_addresses(answer)
    if addresses:
        return failed("dns", f"{hostname} resolves to {', '.join(addresses)}")
    return passed("dns", f"no A or AAAA record for {hostname}")


def proxy_host_ids(payload: str, hostname: str) -> tuple[str, ...]:
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("the NPM answer is not a list")
    return tuple(
        str(row.get("id", "unknown"))
        for row in rows
        if isinstance(row, dict)
        and hostname in (row.get("domain_names") or [])
    )


def rendered_configs(payload: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in payload.splitlines() if line.strip())


def check_no_proxy_host(
    payload: str,
    hostname: str = PUBLIC_HOSTNAME,
    payload_format: str = "json",
) -> Check:
    if payload_format == "config":
        configs = rendered_configs(payload)
        if configs:
            return failed(
                "proxy host",
                f"{len(configs)} rendered config(s) name {hostname}: "
                f"{', '.join(configs)}",
            )
        return passed("proxy host", f"no rendered config names {hostname}")
    try:
        ids = proxy_host_ids(payload, hostname)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return failed("proxy host", f"cannot read the NPM answer: {error}")
    if ids:
        return failed(
            "proxy host",
            f"{len(ids)} NPM host(s) claim {hostname}: {', '.join(ids)}",
        )
    return passed("proxy host", f"no NPM host claims {hostname}")


def has_http_status(code: str) -> bool:
    return code.strip() not in ("", "000")


def check_public_silent(http_code: str, https_code: str) -> Check:
    answers = [
        f"{scheme} answered {code.strip()}"
        for scheme, code in (("http", http_code), ("https", https_code))
        if has_http_status(code)
    ]
    if answers:
        return failed("public host", "; ".join(answers))
    return passed("public host", "neither http nor https answers")


def open_ports(scan: str) -> frozenset[int]:
    ports = set()
    for line in scan.splitlines():
        match = NMAP_PORT_LINE.match(line)
        if match and match.group("state") == "open":
            ports.add(int(match.group("port")))
    return frozenset(ports)


def check_open_ports(
    scan: str, expected: frozenset[int] = EXPECTED_OPEN_PORTS
) -> Check:
    found = open_ports(scan)
    unexpected = sorted(found - expected)
    missing = sorted(expected - found)
    if unexpected or missing:
        problems: list[str] = []
        if unexpected:
            problems.append("also open " + ",".join(map(str, unexpected)))
        if missing:
            problems.append("not open " + ",".join(map(str, missing)))
        return failed("open ports", "; ".join(problems))
    return passed("open ports", "only 80 and 443 answer")


def line_status(line: str) -> str:
    """The status of one printed check, with unknown lines failing closed."""
    token = line.split(maxsplit=1)[0].upper() if line.strip() else ""
    return token if token in STATUSES else FAIL


def verdict(lines: Iterable[str]) -> tuple[str, int]:
    statuses = [line_status(line) for line in lines if line.strip()]
    if not statuses:
        return "verdict: FAIL (no checks ran)", 1
    failed_count = statuses.count(FAIL)
    skipped_count = statuses.count(SKIP)
    total = len(statuses)
    if failed_count:
        summary = (
            f"verdict: FAIL ({failed_count} failed, "
            f"{skipped_count} skipped, {total} check(s))"
        )
        return summary, 1
    if skipped_count:
        summary = (
            f"verdict: INCOMPLETE ({skipped_count} skipped, {total} check(s))"
        )
        return summary, 1
    return f"verdict: PASS ({total} check(s))", 0


def read_stdin() -> str:
    return sys.stdin.read()


def print_check(check: Check) -> int:
    print(check.line())
    return 0 if check.status != FAIL else 1


def command_cookie(_: argparse.Namespace) -> int:
    return print_check(check_login_cookie(read_stdin()))


def command_hsts(_: argparse.Namespace) -> int:
    return print_check(check_hsts(read_stdin()))


def command_dns(args: argparse.Namespace) -> int:
    return print_check(check_no_dns(read_stdin(), args.hostname))


def command_proxy(args: argparse.Namespace) -> int:
    return print_check(
        check_no_proxy_host(read_stdin(), args.hostname, args.format)
    )


def command_public(args: argparse.Namespace) -> int:
    return print_check(check_public_silent(args.http_code, args.https_code))


def command_ports(_: argparse.Namespace) -> int:
    return print_check(check_open_ports(read_stdin()))


def command_status(args: argparse.Namespace) -> int:
    return print_check(check_status(args.name, args.actual, args.expected))


REPORTERS = {PASS: passed, FAIL: failed, SKIP: skipped}


def command_report(args: argparse.Namespace) -> int:
    return print_check(REPORTERS[args.status](args.name, args.detail))


def command_verdict(_: argparse.Namespace) -> int:
    summary, code = verdict(read_stdin().splitlines())
    print(summary)
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release_gate.py")
    commands = parser.add_subparsers(dest="command", required=True)

    cookie = commands.add_parser("cookie")
    cookie.set_defaults(handler=command_cookie)

    hsts = commands.add_parser("hsts")
    hsts.set_defaults(handler=command_hsts)

    dns = commands.add_parser("dns")
    dns.add_argument("--hostname", default=PUBLIC_HOSTNAME)
    dns.set_defaults(handler=command_dns)

    proxy = commands.add_parser("proxy")
    proxy.add_argument("--hostname", default=PUBLIC_HOSTNAME)
    proxy.add_argument("--format", choices=("json", "config"), default="json")
    proxy.set_defaults(handler=command_proxy)

    public = commands.add_parser("public")
    public.add_argument("--http-code", default="000")
    public.add_argument("--https-code", default="000")
    public.set_defaults(handler=command_public)

    ports = commands.add_parser("ports")
    ports.set_defaults(handler=command_ports)

    status = commands.add_parser("status")
    status.add_argument("--name", required=True)
    status.add_argument("--actual", required=True)
    status.add_argument("--expected", type=int, required=True)
    status.set_defaults(handler=command_status)

    report = commands.add_parser("report")
    report.add_argument("--status", choices=tuple(STATUSES), required=True)
    report.add_argument("--name", required=True)
    report.add_argument("--detail", required=True)
    report.set_defaults(handler=command_report)

    result = commands.add_parser("verdict")
    result.set_defaults(handler=command_verdict)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

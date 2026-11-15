"""The release gate: prove the public host is safe, in one script.

Three modes, one at a time. `--pre` proves nothing answers and no proxy host
claims the name. `--release` probes the deployed host. `--ports` scans it from
outside. Each check prints PASS, FAIL or SKIP and the last line is the verdict;
a SKIP makes the run INCOMPLETE, because an unproven item is not a pass.

The decisions are pure functions, unit tested off the network. The orchestration
shells out to curl, dig, docker and nmap.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
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


DEFAULT_TIMEOUT = 10.0
DEFAULT_SEARCH_TIMEOUT = 60.0
DEFAULT_NPM_URL = "http://100.106.27.40:81"
DEFAULT_NPM_CONTAINER = "nginx-app-1"
DOCUMENTATION_PATHS = ("/openapi.json", "/docs", "/redocs", "/scalar")
METADATA_URL = "http://169.254.169.254/latest/meta-data/"
YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def _run(argv: Sequence[str], timeout: float) -> str:
    """Run a command and return its stdout, or "" when it cannot run."""
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout


def _curl_status(
    url: str,
    *,
    insecure: bool = False,
    cookie: str | None = None,
    post: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    argv = [
        "curl",
        "-sS",
        "-o",
        "/dev/null",
        "-w",
        "%{http_code}",
        "--max-time",
        str(timeout),
    ]
    if insecure:
        argv.append("-k")
    if cookie is not None:
        argv += ["-H", f"Cookie: {cookie}"]
    if post is not None:
        argv += [
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "--data-binary",
            post,
        ]
    argv.append(url)
    return _run(argv, timeout + 5) or "000"


def _curl_headers(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    return _run(
        [
            "curl",
            "-sS",
            "-D",
            "-",
            "-o",
            "/dev/null",
            "--max-time",
            str(timeout),
            url,
        ],
        timeout + 5,
    )


def _set_cookie(headers: str) -> str:
    for line in headers.splitlines():
        if line.lower().startswith("set-cookie:"):
            return line.split(":", 1)[1].strip()
    return ""


def _dns(hostname: str) -> str | None:
    """Every address the name resolves to, or None when no tool can look."""
    if shutil.which("dig"):
        return _run(["dig", "+short", "A", hostname], 10) + _run(
            ["dig", "+short", "AAAA", hostname], 10
        )
    if shutil.which("getent"):
        answer = _run(["getent", "ahosts", hostname], 10)
        addresses = {
            line.split()[0] for line in answer.splitlines() if line.strip()
        }
        return "\n".join(sorted(addresses))
    return None


def _npm_container() -> str:
    return _env("NPM_CONTAINER", DEFAULT_NPM_CONTAINER)


def _proxy_format() -> str:
    if _env("NPM_TOKEN", ""):
        return "json"
    if shutil.which("docker") and _run(
        ["docker", "inspect", _npm_container()], 10
    ):
        return "config"
    return "none"


def _proxy_payload(payload_format: str) -> str:
    if payload_format == "json":
        url = _env("NPM_URL", DEFAULT_NPM_URL).rstrip("/")
        token = _env("NPM_TOKEN", "")
        return _run(
            [
                "curl",
                "-sS",
                "--max-time",
                "10",
                "-H",
                f"Authorization: Bearer {token}",
                f"{url}/api/nginx/proxy-hosts",
            ],
            15,
        )
    grep = (
        "grep -l 'server_name .*harpi[.]smileydroid[.]com[.]br' "
        "/data/nginx/proxy_host/*.conf 2>/dev/null"
    )
    return _run(["docker", "exec", _npm_container(), "sh", "-c", grep], 15)


def _cookie_header() -> str:
    value = _env("HARPI_SESSION_COOKIE", "")
    return value if "=" in value else f"__Host-harpi={value}"


def run_pre() -> list[Check]:
    checks: list[Check] = []
    answer = _dns(PUBLIC_HOSTNAME)
    if answer is None:
        checks.append(failed("dns", "neither dig nor getent is installed"))
    else:
        checks.append(check_no_dns(answer, PUBLIC_HOSTNAME))

    payload_format = _proxy_format()
    if payload_format == "none":
        checks.append(
            failed(
                "proxy host",
                "cannot prove absence: set NPM_TOKEN or run on the Docker "
                f"host with {_npm_container()}",
            )
        )
    else:
        checks.append(
            check_no_proxy_host(
                _proxy_payload(payload_format), PUBLIC_HOSTNAME, payload_format
            )
        )

    checks.append(
        check_public_silent(
            _curl_status(f"http://{PUBLIC_HOSTNAME}/", insecure=True),
            _curl_status(f"https://{PUBLIC_HOSTNAME}/", insecure=True),
        )
    )
    return checks


def run_release(base_url: str) -> list[Check]:
    timeout = float(_env("TIMEOUT", str(DEFAULT_TIMEOUT)))
    search_timeout = float(_env("SEARCH_TIMEOUT", str(DEFAULT_SEARCH_TIMEOUT)))
    checks = [
        check_status(
            "unauthenticated /api/session",
            _curl_status(f"{base_url}/api/session", timeout=timeout),
            401,
        ),
        check_hsts(_curl_headers(f"{base_url}/api/session", timeout=timeout)),
    ]
    checks.extend(
        check_status(
            path, _curl_status(f"{base_url}{path}", timeout=timeout), 404
        )
        for path in DOCUMENTATION_PATHS
    )
    checks.append(
        check_login_cookie(
            _set_cookie(
                _curl_headers(f"{base_url}/api/auth/discord", timeout=timeout)
            )
        )
    )

    if not _env("HARPI_SESSION_COOKIE", ""):
        checks.append(
            skipped(
                "ssrf queue probe",
                "no HARPI_SESSION_COOKIE; the URL policy was not exercised",
            )
        )
        checks.append(
            skipped(
                "youtube url accepted",
                "no HARPI_SESSION_COOKIE; the URL policy was not exercised",
            )
        )
        return checks

    cookie = _cookie_header()
    checks.append(
        check_status(
            "authenticated session",
            _curl_status(
                f"{base_url}/api/session", cookie=cookie, timeout=timeout
            ),
            200,
        )
    )
    private_code = _curl_status(
        f"{base_url}/api/queue",
        cookie=cookie,
        post=json.dumps({"url": METADATA_URL}),
        timeout=timeout,
    )
    if private_code == "404":
        checks.append(
            failed(
                "ssrf queue probe",
                "answered 404: connect the bot, select a guild, and retry",
            )
        )
    else:
        checks.append(check_status("ssrf queue probe", private_code, 400))

    checks.append(
        check_status(
            "youtube url accepted",
            _curl_status(
                f"{base_url}/api/search",
                cookie=cookie,
                post=json.dumps({"term": YOUTUBE_URL}),
                timeout=search_timeout,
            ),
            200,
        )
    )
    return checks


def run_ports(host: str) -> list[Check]:
    if not shutil.which("nmap"):
        return [failed("open ports", "nmap is not installed")]
    ports = _env("SCAN_PORTS", "-")
    return [check_open_ports(_run(["nmap", "-Pn", "-p", ports, host], 600))]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release_gate.py")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pre", action="store_true")
    mode.add_argument("--release", action="store_true")
    mode.add_argument("--ports", metavar="HOST")
    parser.add_argument("--base-url")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.release:
        if not args.base_url:
            parser.error("--release needs --base-url")
        if not args.base_url.startswith(("http://", "https://")):
            parser.error(
                f"--base-url takes an http or https URL, not {args.base_url}"
            )
        checks = run_release(args.base_url.rstrip("/"))
    elif args.pre:
        checks = run_pre()
    else:
        checks = run_ports(args.ports)

    lines = [check.line() for check in checks]
    for line in lines:
        print(line)
    summary, code = verdict(lines)
    print(summary)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

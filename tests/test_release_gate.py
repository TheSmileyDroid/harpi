"""Tests for the release gate helpers and CLI against synthetic evidence."""

from __future__ import annotations

import tools.release_gate as release_gate
from tools.release_gate import (
    FAIL,
    PASS,
    check_hsts,
    check_login_cookie,
    check_no_dns,
    check_no_proxy_host,
    check_open_ports,
    check_public_silent,
    check_status,
    header_value,
    line_status,
    main,
    open_ports,
    verdict,
)

HOSTNAME = "harpi.smileydroid.com.br"
GOOD_COOKIE = "__Host-harpi=abc; Secure; HttpOnly; SameSite=Lax; Path=/"
GOOD_HSTS = "Strict-Transport-Security: max-age=31536000"
SCAN = """
Starting Nmap 7.95
PORT     STATE    SERVICE
22/tcp   filtered ssh
80/tcp   open     http
443/tcp  open     https
8000/tcp closed   http-alt
"""


def test_a_login_cookie_with_every_flag_passes():
    check = check_login_cookie(GOOD_COOKIE)

    assert check.status == PASS
    assert "__Host-harpi" in check.detail


def test_a_login_cookie_without_the_host_prefix_fails():
    check = check_login_cookie(GOOD_COOKIE.replace("__Host-", ""))

    assert check.status == FAIL
    assert "__Host-" in check.detail


def test_a_login_cookie_without_secure_fails():
    check = check_login_cookie(GOOD_COOKIE.replace("; Secure", ""))

    assert check.status == FAIL
    assert "Secure" in check.detail


def test_a_login_cookie_without_httponly_fails():
    check = check_login_cookie(GOOD_COOKIE.replace("; HttpOnly", ""))

    assert check.status == FAIL
    assert "HttpOnly" in check.detail


def test_a_login_cookie_with_a_different_samesite_fails():
    check = check_login_cookie(
        GOOD_COOKIE.replace("SameSite=Lax", "SameSite=Strict")
    )

    assert check.status == FAIL
    assert "SameSite" in check.detail


def test_a_login_cookie_with_a_different_path_fails():
    check = check_login_cookie(GOOD_COOKIE.replace("Path=/", "Path=/api"))

    assert check.status == FAIL
    assert "Path" in check.detail


def test_a_login_cookie_with_a_domain_fails():
    check = check_login_cookie(f"{GOOD_COOKIE}; Domain=smileydroid.com.br")

    assert check.status == FAIL
    assert "Domain" in check.detail


def test_a_login_response_without_a_cookie_fails():
    check = check_login_cookie("")

    assert check.status == FAIL
    assert "Set-Cookie" in check.detail


def test_hsts_without_subdomains_passes():
    check = check_hsts(GOOD_HSTS)

    assert check.status == PASS
    assert "max-age=31536000" in check.detail


def test_hsts_with_subdomains_fails():
    check = check_hsts(f"{GOOD_HSTS}; includeSubDomains")

    assert check.status == FAIL
    assert "subdomains" in check.detail


def test_hsts_without_max_age_fails():
    check = check_hsts("Strict-Transport-Security: preload")

    assert check.status == FAIL
    assert "max-age" in check.detail


def test_hsts_with_zero_max_age_fails():
    check = check_hsts("Strict-Transport-Security: max-age=0")

    assert check.status == FAIL
    assert "max-age=0" in check.detail


def test_a_response_without_hsts_fails():
    check = check_hsts("Content-Type: text/html")

    assert check.status == FAIL
    assert "Strict-Transport-Security" in check.detail


def test_a_header_is_read_with_any_case():
    assert (
        header_value(
            "Strict-Transport-Security: max-age=1", "strict-transport-security"
        )
        == "max-age=1"
    )


def test_a_missing_header_is_empty():
    assert (
        header_value("Content-Type: text/html", "strict-transport-security")
        == ""
    )


def test_a_scan_with_only_80_and_443_open_passes():
    check = check_open_ports(SCAN)

    assert check.status == PASS
    assert open_ports(SCAN) == frozenset({80, 443})


def test_an_extra_open_port_fails():
    check = check_open_ports(f"{SCAN}\n81/tcp open http\n")

    assert check.status == FAIL
    assert "also open 81" in check.detail


def test_a_missing_open_port_fails():
    check = check_open_ports(SCAN.replace("443/tcp  open     https", ""))

    assert check.status == FAIL
    assert "not open 443" in check.detail


def test_a_scan_with_no_open_ports_fails():
    check = check_open_ports("Host seems down.\n")

    assert check.status == FAIL
    assert "not open 80,443" in check.detail


def test_an_empty_dns_answer_passes():
    check = check_no_dns("", HOSTNAME)

    assert check.status == PASS
    assert HOSTNAME in check.detail


def test_a_resolving_name_fails():
    check = check_no_dns("203.0.113.10\n", HOSTNAME)

    assert check.status == FAIL
    assert "203.0.113.10" in check.detail


def test_an_empty_npm_host_list_passes():
    check = check_no_proxy_host("[]", HOSTNAME)

    assert check.status == PASS


def test_an_npm_host_claiming_the_name_fails():
    payload = f'[{{"id": 7, "domain_names": ["{HOSTNAME}"]}}]'

    check = check_no_proxy_host(payload, HOSTNAME)

    assert check.status == FAIL
    assert "7" in check.detail


def test_an_npm_host_for_another_name_passes():
    payload = '[{"id": 7, "domain_names": ["other.example"]}]'

    check = check_no_proxy_host(payload, HOSTNAME)

    assert check.status == PASS


def test_rendered_configs_naming_the_host_fail():
    payload = "/data/nginx/proxy_host/1.conf\n/data/nginx/proxy_host/2.conf\n"

    check = check_no_proxy_host(payload, HOSTNAME, payload_format="config")

    assert check.status == FAIL
    assert "2 rendered config" in check.detail


def test_no_rendered_configs_pass():
    check = check_no_proxy_host("", HOSTNAME, payload_format="config")

    assert check.status == PASS


def test_a_malformed_npm_answer_fails():
    check = check_no_proxy_host("not json", HOSTNAME)

    assert check.status == FAIL
    assert "cannot read" in check.detail


def test_silent_http_codes_pass():
    check = check_public_silent("000", "000")

    assert check.status == PASS


def test_an_http_answer_fails():
    check = check_public_silent("200", "000")

    assert check.status == FAIL
    assert "http answered 200" in check.detail


def test_an_https_answer_fails():
    check = check_public_silent("000", "301")

    assert check.status == FAIL
    assert "https answered 301" in check.detail


def test_a_matching_status_passes():
    check = check_status("unauthenticated /api/session", "401", 401)

    assert check.status == PASS


def test_a_different_status_fails():
    check = check_status("unauthenticated /api/session", "200", 401)

    assert check.status == FAIL
    assert "expected 401" in check.detail


def test_a_check_line_names_its_status_and_check():
    check = check_status("/docs", "404", 404)

    assert check.line() == "PASS /docs: answered 404"


def test_one_fail_makes_the_run_fail():
    summary, code = verdict([
        "PASS dns: empty",
        "FAIL proxy host: 1",
        "SKIP ssrf",
    ])

    assert code == 1
    assert "FAIL" in summary
    assert "1 failed" in summary
    assert "1 skipped" in summary


def test_all_pass_makes_the_run_pass():
    summary, code = verdict(["PASS dns: empty", "PASS hsts: max-age=1"])

    assert code == 0
    assert "PASS" in summary
    assert "skipped" not in summary


def test_a_skip_makes_the_run_incomplete():
    summary, code = verdict([
        "PASS dns: empty",
        "SKIP ssrf queue probe: no cookie",
    ])

    assert code == 1
    assert "INCOMPLETE" in summary
    assert "1 skipped" in summary


def test_an_unrecognised_line_fails():
    summary, code = verdict(["garbage"])

    assert code == 1
    assert "FAIL" in summary
    assert line_status("garbage") == FAIL


def test_no_checks_fails():
    summary, code = verdict([])

    assert code == 1
    assert "no checks ran" in summary


def test_pre_passes_when_nothing_answers(monkeypatch, capsys):
    monkeypatch.setattr(release_gate, "_dns", lambda hostname: "")
    monkeypatch.setattr(release_gate, "_proxy_format", lambda: "config")
    monkeypatch.setattr(release_gate, "_proxy_payload", lambda *_: "")
    monkeypatch.setattr(release_gate, "_curl_status", lambda url, **kw: "000")

    code = main(["--pre"])

    assert code == 0
    assert "verdict: PASS" in capsys.readouterr().out


def test_pre_fails_when_the_public_host_answers(monkeypatch, capsys):
    monkeypatch.setattr(release_gate, "_dns", lambda hostname: "203.0.113.9")
    monkeypatch.setattr(release_gate, "_proxy_format", lambda: "none")
    monkeypatch.setattr(release_gate, "_curl_status", lambda url, **kw: "200")

    code = main(["--pre"])

    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL dns" in out
    assert "FAIL public host" in out


def test_release_skips_the_authenticated_probes_without_a_cookie(
    monkeypatch, capsys
):
    monkeypatch.delenv("HARPI_SESSION_COOKIE", raising=False)

    def status(url, **kw):
        return "401" if url.endswith("/api/session") else "404"

    monkeypatch.setattr(release_gate, "_curl_status", status)
    monkeypatch.setattr(
        release_gate,
        "_curl_headers",
        lambda url, **kw: (
            "Strict-Transport-Security: max-age=31536000\r\nSet-Cookie: "
            + GOOD_COOKIE
        ),
    )

    code = main(["--release", "--base-url", "https://example.test"])

    out = capsys.readouterr().out
    assert code == 1
    assert "SKIP ssrf queue probe" in out
    assert "verdict: INCOMPLETE" in out


def test_release_needs_a_base_url(capsys):
    try:
        main(["--release"])
    except SystemExit as exit_error:
        assert exit_error.code == 2
    else:  # pragma: no cover - argparse always exits
        raise AssertionError("argparse accepted --release without --base-url")
    assert "--base-url" in capsys.readouterr().err


def test_ports_fails_when_nmap_is_missing(monkeypatch, capsys):
    monkeypatch.setattr(release_gate.shutil, "which", lambda name: None)

    code = main(["--ports", "example.test"])

    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL open ports" in out

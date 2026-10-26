"""Source policy: which URLs may reach yt-dlp, and how the client is configured."""

from __future__ import annotations

import http.server
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace

import pytest

from src.config import Settings
from src.harpi_lib.music.source_policy import (
    SourcePolicyError,
    check_source,
    check_url,
    fetch_redirect_location,
    follow_checked_redirects,
    host_of,
    is_source_url,
    public_host_allowed,
    refused_address_reason,
)
from src.harpi_lib.music.ytdl_options import build_ytdl_options

PUBLIC_ADDRESS = "142.251.152.4"


def public_resolver(host: str) -> tuple[str, ...]:
    return (PUBLIC_ADDRESS,)


def resolver_for(**addresses: str):
    def resolve(host: str) -> tuple[str, ...]:
        if host not in addresses:
            raise OSError(f"{host} is unknown to this resolver")
        return (addresses[host],)

    return resolve


class _RedirectingHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self.send_response(302)
        self.send_header("Location", "https://www.youtube.com/watch?v=1")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


class _PlainHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def local_server(
    handler: type[http.server.BaseHTTPRequestHandler],
) -> Iterator[http.server.HTTPServer]:
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


YOUTUBE_URLS = [
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://youtube-nocookie.com/embed/dQw4w9WgXcQ",
    "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
    "https://rr1---sn-abc.googlevideo.com/videoplayback?expire=1",
    "https://redirector.googlevideo.com/videoplayback?id=1",
    "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    "https://yt3.ggpht.com/avatar",
]


@pytest.mark.parametrize("url", YOUTUBE_URLS)
def test_public_mode_accepts_youtube_and_its_cdn(url: str):
    assert check_url(url, public_mode=True, resolver=public_resolver) == url


@pytest.mark.parametrize("url", YOUTUBE_URLS)
def test_lan_mode_accepts_youtube_and_its_cdn(url: str):
    assert check_url(url, public_mode=False, resolver=public_resolver) == url


def test_public_mode_accepts_a_trailing_dot_host():
    url = "https://www.youtube.com./watch?v=dQw4w9WgXcQ"

    assert check_url(url, public_mode=True, resolver=public_resolver) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/song",
        "https://vimeo.com/12345",
        "https://youtube.com.evil.test/watch?v=1",
        "https://notyoutube.com/watch?v=1",
        "https://youtu.be.evil.test/1",
    ],
)
def test_public_mode_refuses_a_non_youtube_host(url: str):
    with pytest.raises(SourcePolicyError, match="not a YouTube source"):
        check_url(url, public_mode=True, resolver=public_resolver)


def test_lan_mode_accepts_a_non_youtube_host():
    url = "https://example.com/song"

    assert check_url(url, public_mode=False, resolver=public_resolver) == url


@pytest.mark.parametrize(
    ("address", "reason"),
    [
        ("127.0.0.1", "loopback address"),
        ("127.9.9.9", "loopback address"),
        ("::1", "loopback address"),
        ("::ffff:127.0.0.1", "loopback address"),
        ("169.254.169.254", "cloud metadata address"),
        ("169.254.1.1", "link-local address"),
        ("fe80::1", "link-local address"),
        ("10.1.2.3", "private network address"),
        ("172.16.0.1", "private network address"),
        ("192.168.0.10", "private network address"),
        ("100.64.0.1", "private network address"),
        ("fd00::1", "private network address"),
        ("224.0.0.1", "multicast address"),
        ("ff02::1", "multicast address"),
        ("0.0.0.0", "reserved address"),
        ("240.0.0.1", "reserved address"),
        ("::", "reserved address"),
    ],
)
def test_addresses_that_cannot_be_public_are_named(address: str, reason: str):
    assert refused_address_reason(address) == reason


@pytest.mark.parametrize(
    "address", ["8.8.8.8", "142.251.152.4", "2a00:1450:4001:80f::200e"]
)
def test_public_addresses_are_accepted(address: str):
    assert refused_address_reason(address) is None


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.10/",
        "http://10.0.0.5/",
        "http://172.16.0.1/",
        "http://100.64.0.1/",
        "http://224.0.0.1/",
        "http://[fe80::1]/",
    ],
)
@pytest.mark.parametrize("public_mode", [True, False])
def test_private_literal_addresses_are_refused_in_both_modes(
    url: str, public_mode: bool
):
    with pytest.raises(SourcePolicyError):
        check_url(url, public_mode=public_mode, resolver=public_resolver)


def test_a_hostname_resolving_to_loopback_is_refused():
    with pytest.raises(SourcePolicyError, match="loopback address"):
        check_url(
            "http://internal.test:9099/",
            public_mode=False,
            resolver=resolver_for(**{"internal.test": "127.0.0.1"}),
        )


def test_a_hostname_resolving_to_rfc1918_is_refused():
    with pytest.raises(SourcePolicyError, match="private network address"):
        check_url(
            "http://router.local/",
            public_mode=False,
            resolver=resolver_for(**{"router.local": "192.168.1.1"}),
        )


def test_a_metadata_hostname_is_refused():
    with pytest.raises(SourcePolicyError, match="cloud metadata address"):
        check_url(
            "http://metadata.google.internal/computeMetadata/v1/",
            public_mode=False,
            resolver=resolver_for(**{
                "metadata.google.internal": "169.254.169.254"
            }),
        )


def test_one_private_answer_among_public_answers_is_refused():
    def resolve(host: str) -> tuple[str, ...]:
        return (PUBLIC_ADDRESS, "10.0.0.7")

    with pytest.raises(SourcePolicyError, match="private network address"):
        check_url("https://example.com/", public_mode=False, resolver=resolve)


def test_wildcard_dns_services_are_refused_when_they_resolve_private():
    resolve = resolver_for(**{
        "169.254.169.254.nip.io": "169.254.169.254",
        "127.0.0.1.sslip.io": "127.0.0.1",
    })

    with pytest.raises(SourcePolicyError, match="cloud metadata address"):
        check_url(
            "http://169.254.169.254.nip.io/",
            public_mode=False,
            resolver=resolve,
        )
    with pytest.raises(SourcePolicyError, match="loopback address"):
        check_url(
            "http://127.0.0.1.sslip.io/", public_mode=False, resolver=resolve
        )


def test_an_allowlisted_host_resolving_private_is_refused_in_public_mode():
    with pytest.raises(SourcePolicyError, match="loopback address"):
        check_url(
            "https://www.youtube.com/watch?v=1",
            public_mode=True,
            resolver=resolver_for(**{"www.youtube.com": "127.0.0.1"}),
        )


def test_an_unresolvable_host_is_refused():
    def resolve(host: str) -> tuple[str, ...]:
        raise OSError("no answer")

    with pytest.raises(SourcePolicyError, match="could not be resolved"):
        check_url("https://example.com/", public_mode=False, resolver=resolve)


def test_a_host_without_addresses_is_refused():
    with pytest.raises(SourcePolicyError, match="could not be resolved"):
        check_url(
            "https://example.com/", public_mode=False, resolver=lambda host: ()
        )


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("file:///etc/passwd", "only http and https"),
        ("ftp://www.youtube.com/watch?v=1", "only http and https"),
        ("gopher://www.youtube.com/", "only http and https"),
        ("javascript:alert(1)", "only http and https"),
        ("http://user:pass@www.youtube.com/watch?v=1", "embedded credentials"),
        ("http://user@www.youtube.com/watch?v=1", "embedded credentials"),
        ("http://@www.youtube.com/watch?v=1", "embedded credentials"),
        ("http:///watch?v=1", "no host"),
    ],
)
def test_schemes_and_credentials_are_refused(url: str, reason: str):
    with pytest.raises(SourcePolicyError, match=reason):
        check_url(url, public_mode=False, resolver=public_resolver)


def test_a_malformed_url_is_refused():
    with pytest.raises(SourcePolicyError, match="malformed URL"):
        check_url("http://[::1/", public_mode=False, resolver=public_resolver)


def test_host_of_normalizes_the_host():
    assert host_of("https://WWW.YouTube.COM./watch?v=1") == "www.youtube.com"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://www.youtube.com/watch?v=1", True),
        ("HTTP://example.com/", True),
        ("ftp://example.com/x", True),
        ("some song", False),
        ("AC/DC thunderstruck", False),
        ("d:ream things can only get better", False),
    ],
)
def test_is_source_url_separates_links_from_search_terms(
    value: str, expected: bool
):
    assert is_source_url(value) is expected


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("youtube.com", True),
        ("www.youtube.com", True),
        ("m.youtube.com", True),
        ("music.youtube.com", True),
        ("youtu.be", True),
        ("www.youtube-nocookie.com", True),
        ("rr3---sn-abc.googlevideo.com", True),
        ("i.ytimg.com", True),
        ("yt3.ggpht.com", True),
        ("example.com", False),
        ("youtube.com.evil.test", False),
        ("evilgooglevideo.com", False),
        ("consent.youtube.com", False),
    ],
)
def test_public_host_allowed_matches_youtube_and_its_cdn(
    host: str, expected: bool
):
    assert public_host_allowed(host) is expected


def test_a_redirect_to_a_private_address_is_refused():
    def fetch(url: str) -> str | None:
        return "http://192.168.1.1/admin"

    with pytest.raises(SourcePolicyError, match="private network address"):
        follow_checked_redirects(
            "https://example.com/watch",
            public_mode=False,
            resolver=public_resolver,
            fetch_location=fetch,
        )


def test_a_redirect_to_the_metadata_address_is_refused():
    def fetch(url: str) -> str | None:
        return "http://169.254.169.254/latest/meta-data/"

    with pytest.raises(SourcePolicyError, match="cloud metadata address"):
        follow_checked_redirects(
            "https://example.com/watch",
            public_mode=False,
            resolver=public_resolver,
            fetch_location=fetch,
        )


def test_a_public_mode_redirect_off_youtube_is_refused():
    def fetch(url: str) -> str | None:
        return "https://example.com/song"

    with pytest.raises(SourcePolicyError, match="not a YouTube source"):
        follow_checked_redirects(
            "https://youtu.be/dQw4w9WgXcQ",
            public_mode=True,
            resolver=public_resolver,
            fetch_location=fetch,
        )


def test_a_redirect_inside_the_policy_is_followed():
    hops = {
        "https://youtu.be/dQw4w9WgXcQ": (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ),
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": None,
    }

    final = follow_checked_redirects(
        "https://youtu.be/dQw4w9WgXcQ",
        public_mode=True,
        resolver=public_resolver,
        fetch_location=hops.__getitem__,
    )

    assert final == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_a_relative_redirect_is_resolved_against_its_origin():
    hops = {
        "https://www.youtube.com/watch?v=1": "/watch?v=2",
        "https://www.youtube.com/watch?v=2": None,
    }

    final = follow_checked_redirects(
        "https://www.youtube.com/watch?v=1",
        public_mode=True,
        resolver=public_resolver,
        fetch_location=hops.__getitem__,
    )

    assert final == "https://www.youtube.com/watch?v=2"


def test_a_redirect_loop_stops_at_the_limit():
    with pytest.raises(SourcePolicyError, match="too many redirects"):
        follow_checked_redirects(
            "https://example.com/1",
            public_mode=False,
            resolver=public_resolver,
            fetch_location=lambda url: "https://example.com/1",
            limit=3,
        )


def test_public_mode_source_check_walks_redirects():
    def fetch(url: str) -> str | None:
        return "https://www.youtube.com/watch?v=evil"

    with pytest.raises(SourcePolicyError, match="private network address"):
        check_source(
            "https://youtu.be/dQw4w9WgXcQ",
            public_mode=True,
            resolver=resolver_for(**{
                "youtu.be": PUBLIC_ADDRESS,
                "www.youtube.com": "10.0.0.1",
            }),
            fetch_location=fetch,
        )


def test_lan_mode_source_check_never_fetches():
    def fetch(url: str) -> str | None:
        raise AssertionError("LAN mode must not fetch")

    assert (
        check_source(
            "https://example.com/song",
            public_mode=False,
            resolver=public_resolver,
            fetch_location=fetch,
        )
        == "https://example.com/song"
    )


def test_fetch_redirect_location_reports_the_target_without_following():
    with local_server(_RedirectingHandler) as server:
        location = fetch_redirect_location(
            f"http://127.0.0.1:{server.server_port}/watch"
        )

    assert location == "https://www.youtube.com/watch?v=1"


def test_fetch_redirect_location_answers_none_without_a_redirect():
    with local_server(_PlainHandler) as server:
        location = fetch_redirect_location(
            f"http://127.0.0.1:{server.server_port}/"
        )

    assert location is None


def test_fetch_redirect_location_refuses_an_unreachable_host():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    with pytest.raises(SourcePolicyError, match="could not be reached"):
        fetch_redirect_location(f"http://127.0.0.1:{port}/")


def test_an_unparseable_address_is_named():
    assert refused_address_reason("not-an-address") == "unparseable address"


def test_public_mode_options_restrict_extractors_and_playlists():
    options = build_ytdl_options(
        replace(Settings.from_env(), public_mode=True)
    )

    assert options["allowed_extractors"] == [
        "youtube",
        "youtube:tab",
        "youtube:search",
    ]
    assert options["noplaylist"] is False
    assert options["playlist_items"] == "1"


def test_lan_mode_options_keep_the_broad_extractor_set():
    options = build_ytdl_options(
        replace(Settings.from_env(), public_mode=False)
    )

    assert "allowed_extractors" not in options
    assert options["noplaylist"] is False
    assert "playlist_items" not in options


def test_options_carry_the_cookie_file_and_js_runtimes():
    options = build_ytdl_options(
        Settings.from_env(),
        cookiefile="/run/cookies.txt",
        js_runtimes={"deno": {"path": "/usr/bin/deno"}},
    )

    assert options["cookiefile"] == "/run/cookies.txt"
    assert options["js_runtimes"] == {"deno": {"path": "/usr/bin/deno"}}


def test_options_place_output_under_the_configured_work_dir():
    settings = replace(Settings.from_env(), work_dir="/srv/harpi/work")

    options = build_ytdl_options(settings)

    assert options["outtmpl"].startswith("/srv/harpi/work/audios/")
    assert options["cachedir"] == "/srv/harpi/work/yt-dlp-cache"

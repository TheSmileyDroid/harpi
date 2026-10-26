"""Which URLs the music source may hand to yt-dlp.

The decision is pure: the resolver and the redirect fetcher are arguments,
so every branch is testable without the network.  A refused URL raises
:class:`SourcePolicyError`, whose message says which rule it broke.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit

Resolver = Callable[[str], tuple[str, ...]]
RedirectFetcher = Callable[[str], str | None]

WEB_SCHEMES = frozenset({"http", "https"})
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
REDIRECT_LIMIT = 5
PREFLIGHT_TIMEOUT_SECONDS = 5.0
PREFLIGHT_USER_AGENT = "Mozilla/5.0 (compatible; harpi-source-check)"

YOUTUBE_HOSTS = frozenset({
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
})
YOUTUBE_DOMAINS = ("googlevideo.com", "ytimg.com", "ggpht.com")

CLOUD_METADATA_ADDRESS = ipaddress.ip_address("169.254.169.254")

RefusedNetwork = tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, str]
REFUSED_NETWORKS: tuple[RefusedNetwork, ...] = (
    (ipaddress.ip_network("127.0.0.0/8"), "loopback address"),
    (ipaddress.ip_network("::1/128"), "loopback address"),
    (ipaddress.ip_network("169.254.0.0/16"), "link-local address"),
    (ipaddress.ip_network("fe80::/10"), "link-local address"),
    (ipaddress.ip_network("10.0.0.0/8"), "private network address"),
    (ipaddress.ip_network("172.16.0.0/12"), "private network address"),
    (ipaddress.ip_network("192.168.0.0/16"), "private network address"),
    (ipaddress.ip_network("100.64.0.0/10"), "private network address"),
    (ipaddress.ip_network("fc00::/7"), "private network address"),
    (ipaddress.ip_network("224.0.0.0/4"), "multicast address"),
    (ipaddress.ip_network("ff00::/8"), "multicast address"),
    (ipaddress.ip_network("0.0.0.0/8"), "reserved address"),
    (ipaddress.ip_network("240.0.0.0/4"), "reserved address"),
    (ipaddress.ip_network("::/128"), "reserved address"),
)


class SourcePolicyError(ValueError):
    """A URL the source policy refuses to hand to yt-dlp."""


def is_source_url(value: str) -> bool:
    """True when *value* names a URL rather than a search term."""
    return "://" in value or value.lower().startswith(("http:", "https:"))


def host_of(url: str) -> str:
    """The host of *url*, refusing schemes, credentials, and empty hosts."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
        has_credentials = (
            parts.username is not None or parts.password is not None
        )
    except ValueError as exc:
        raise SourcePolicyError("malformed URL") from exc
    if parts.scheme.lower() not in WEB_SCHEMES:
        raise SourcePolicyError("only http and https URLs are accepted")
    if has_credentials:
        raise SourcePolicyError("URLs with embedded credentials are refused")
    if not host:
        raise SourcePolicyError("URL has no host")
    return host


def public_host_allowed(host: str) -> bool:
    """True when *host* is YouTube or one of its CDN domains."""
    if host in YOUTUBE_HOSTS:
        return True
    return any(
        host == domain or host.endswith(f".{domain}")
        for domain in YOUTUBE_DOMAINS
    )


def refused_address_reason(address: str) -> str | None:
    """Why *address* cannot be fetched, or None when it is publicly routed."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return "unparseable address"
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
        parsed = parsed.ipv4_mapped
    if parsed == CLOUD_METADATA_ADDRESS:
        return "cloud metadata address"
    for network, reason in REFUSED_NETWORKS:
        if parsed in network:
            return reason
    return None


def resolve_host_addresses(host: str) -> tuple[str, ...]:
    """Resolve *host* through the system resolver."""
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return tuple(sorted({info[4][0] for info in infos}))


def check_host_addresses(host: str, resolver: Resolver) -> None:
    """Refuse *host* when any address the resolver returns is not public."""
    try:
        addresses = resolver(host)
    except OSError as exc:
        raise SourcePolicyError(f"{host} could not be resolved") from exc
    if not addresses:
        raise SourcePolicyError(f"{host} could not be resolved")
    for address in addresses:
        reason = refused_address_reason(address)
        if reason is not None:
            raise SourcePolicyError(f"{host} resolves to a {reason}")


def literal_address(host: str) -> str | None:
    """The address *host* spells out, or None when it is a name."""
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return None


def check_url(
    url: str, *, public_mode: bool, resolver: Resolver | None = None
) -> str:
    """Refuse *url* unless its scheme, host, and addresses satisfy the policy."""
    host = host_of(url)
    if public_mode and not public_host_allowed(host):
        raise SourcePolicyError(f"{host} is not a YouTube source")
    literal = literal_address(host)
    if literal is not None:
        reason = refused_address_reason(literal)
        if reason is not None:
            raise SourcePolicyError(f"{host} is a {reason}")
        return url
    check_host_addresses(host, resolver or resolve_host_addresses)
    return url


def check_redirect(
    origin: str,
    location: str,
    *,
    public_mode: bool,
    resolver: Resolver | None = None,
) -> str:
    """Refuse a redirect *location* that leaves the source policy."""
    return check_url(
        urljoin(origin, location), public_mode=public_mode, resolver=resolver
    )


def follow_checked_redirects(
    url: str,
    *,
    public_mode: bool,
    resolver: Resolver | None = None,
    fetch_location: RedirectFetcher | None = None,
    limit: int = REDIRECT_LIMIT,
) -> str:
    """Check *url* and each redirect it answers, returning the final URL."""
    fetch = fetch_location or fetch_redirect_location
    current = check_url(url, public_mode=public_mode, resolver=resolver)
    for _ in range(limit):
        location = fetch(current)
        if location is None:
            return current
        current = check_redirect(
            current, location, public_mode=public_mode, resolver=resolver
        )
    raise SourcePolicyError("too many redirects")


def check_source(
    url: str,
    *,
    public_mode: bool,
    resolver: Resolver | None = None,
    fetch_location: RedirectFetcher | None = None,
) -> str:
    """Check a user-supplied source; public mode also walks its redirects."""
    if not public_mode:
        return check_url(url, public_mode=False, resolver=resolver)
    return follow_checked_redirects(
        url,
        public_mode=True,
        resolver=resolver,
        fetch_location=fetch_location,
    )


def fetch_redirect_location(url: str) -> str | None:
    """Ask *url* for a redirect target without following it."""
    parts = urlsplit(url)
    connection_class = (
        http.client.HTTPSConnection
        if parts.scheme == "https"
        else http.client.HTTPConnection
    )
    connection = connection_class(
        parts.hostname, parts.port, timeout=PREFLIGHT_TIMEOUT_SECONDS
    )
    try:
        connection.request(
            "HEAD",
            urlunsplit(("", "", parts.path or "/", parts.query, "")),
            headers={"User-Agent": PREFLIGHT_USER_AGENT},
        )
        response = connection.getresponse()
        location = response.getheader("Location")
        return location if response.status in REDIRECT_CODES else None
    except (OSError, http.client.HTTPException) as exc:
        raise SourcePolicyError(f"{url} could not be reached") from exc
    finally:
        connection.close()

"""SSRF guard: refuse URLs that lead to private, loopback or otherwise internal addresses."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable

import httpx

from .fetcher import FetchError

ALLOWED_PORTS = frozenset({80, 443})
NAT64 = ipaddress.ip_network("64:ff9b::/96")

Resolver = Callable[[str, int], list[str]]


def system_resolver(host: str, port: int) -> list[str]:
    """Resolve host to every IP address the operating system knows for it."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as error:
        raise FetchError(f"Could not resolve host: {host}") from error
    return [str(info[4][0]) for info in infos]


def is_public_address(address: str) -> bool:
    """True only for globally routable unicast addresses. Anything unclear is refused."""
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
    except ValueError:
        return False

    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped
        if embedded is None:
            embedded = ip.sixtofour
        if embedded is None and ip in NAT64:
            embedded = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        if embedded is not None:
            return is_public_address(str(embedded))

    return ip.is_global and not ip.is_multicast


def validate_url(url: str, resolver: Resolver = system_resolver) -> list[str]:
    """Raise FetchError unless url is a plain http(s) URL whose host resolves only to public IPs.

    Returns the addresses that were checked.
    """
    try:
        target = httpx.URL(url)
    except httpx.InvalidURL as error:
        raise FetchError("Invalid URL") from error

    if target.scheme not in ("http", "https"):
        raise FetchError(f"Unsupported URL scheme: {target.scheme or 'none'}")
    if not target.host:
        raise FetchError("URL has no host")
    if target.userinfo:
        raise FetchError("URLs with embedded credentials are not allowed")

    port = target.port or (443 if target.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise FetchError(f"Port {port} is not allowed")

    addresses = resolver(target.host, port)
    if not addresses:
        raise FetchError(f"Could not resolve host: {target.host}")
    if not all(is_public_address(address) for address in addresses):
        raise FetchError("Refusing to fetch: the host points to a non-public address")
    return addresses


def make_validator(resolver: Resolver = system_resolver) -> Callable[[str], list[str]]:
    """Build the validator that fetcher.fetch runs on the first URL and on every redirect.

    It returns the addresses it approved, and fetch connects to exactly those.
    """

    def validate(url: str) -> list[str]:
        return validate_url(url, resolver)

    return validate
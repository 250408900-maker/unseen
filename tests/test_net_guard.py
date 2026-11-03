import socket

import pytest

from unseen.fetcher import FetchError, fetch
from unseen.net_guard import is_public_address, make_validator, system_resolver, validate_url

PUBLIC = ["93.184.216.34", "8.8.8.8", "1.1.1.1", "2606:2800:220:1:248:1893:25c8:1946"]

NON_PUBLIC = [
    "127.0.0.1",
    "127.255.255.254",
    "10.0.0.1",
    "172.16.0.1",
    "172.31.255.255",
    "192.168.1.1",
    "169.254.169.254",  # cloud metadata service
    "0.0.0.0",
    "100.64.0.1",
    "224.0.0.1",
    "240.0.0.1",
    "255.255.255.255",
    "::1",
    "::",
    "fe80::1",
    "fe80::1%eth0",
    "fc00::1",
    "fd12:3456:789a::1",
    "::ffff:127.0.0.1",
    "::ffff:10.0.0.1",
    "::ffff:169.254.169.254",
    "64:ff9b::7f00:1",
    "2002:7f00:1::",
    "2002:a9fe:a9fe::",
    "not-an-ip",
    "",
    "2130706433",
]

BLOCKED_URLS = [
    "http://127.0.0.1/",
    "http://127.0.0.1:80/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/",
    "http://192.168.0.1/admin",
    "http://localhost/",
    "http://2130706433/",
    "http://0x7f.0.0.1/",
    "http://017700000001/",
]


def echo(host, port):
    """Fake resolver for IP literals: the 'resolved' address is the host itself."""
    return [host]


def returns(*addresses):
    return lambda host, port: list(addresses)


@pytest.mark.parametrize("address", PUBLIC)
def test_public_addresses_are_allowed(address):
    assert is_public_address(address)


@pytest.mark.parametrize("address", NON_PUBLIC)
def test_non_public_addresses_are_refused(address):
    assert not is_public_address(address)


def test_valid_url_returns_checked_addresses():
    result = validate_url("https://example.com/page", returns("93.184.216.34"))
    assert result == ["93.184.216.34"]


@pytest.mark.parametrize("url", BLOCKED_URLS)
def test_internal_urls_are_blocked(url):
    with pytest.raises(FetchError):
        validate_url(url, echo)


def test_one_bad_address_blocks_the_whole_host():
    with pytest.raises(FetchError):
        validate_url("http://example.com/", returns("93.184.216.34", "127.0.0.1"))


def test_host_with_no_addresses_is_refused():
    with pytest.raises(FetchError):
        validate_url("http://example.com/", returns())


def test_error_does_not_reveal_the_internal_address():
    with pytest.raises(FetchError) as info:
        validate_url("http://evil.example/", returns("10.1.2.3"))
    assert "10.1.2.3" not in str(info.value)


@pytest.mark.parametrize(
    "url",
    ["http://example.com:8080/", "https://example.com:8443/", "http://example.com:22/"],
)
def test_unusual_ports_are_blocked(url):
    with pytest.raises(FetchError):
        validate_url(url, returns("93.184.216.34"))


@pytest.mark.parametrize("url", ["http://example.com:80/", "https://example.com:443/"])
def test_standard_ports_are_allowed(url):
    assert validate_url(url, returns("93.184.216.34"))


@pytest.mark.parametrize(
    "url",
    ["http://user:pass@example.com/", "http://evil.com@127.0.0.1/", "https://a:b@example.com/"],
)
def test_embedded_credentials_are_blocked(url):
    with pytest.raises(FetchError):
        validate_url(url, returns("93.184.216.34"))


@pytest.mark.parametrize(
    "url",
    ["ftp://example.com/", "file:///etc/passwd", "gopher://example.com/", "javascript:alert(1)"],
)
def test_other_schemes_are_blocked(url):
    with pytest.raises(FetchError):
        validate_url(url, returns("93.184.216.34"))


@pytest.mark.parametrize("url", ["", "http://", "not a url"])
def test_invalid_urls_are_blocked(url):
    with pytest.raises(FetchError):
        validate_url(url, returns("93.184.216.34"))


def test_resolver_failure_becomes_fetch_error(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(FetchError):
        system_resolver("nope.invalid", 80)


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://localhost/"])
def test_fetch_refuses_localhost_before_connecting(url):
    with pytest.raises(FetchError):
        fetch(url, validator=make_validator())
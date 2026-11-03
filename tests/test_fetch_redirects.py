import httpx
import pytest

from unseen.fetcher import FetchError, fetch, pin_request
from unseen.net_guard import make_validator

PUBLIC_IP = "93.184.216.34"
PUBLIC_IPV6 = "2606:2800:220:1:248:1893:25c8:1946"


def resolver(host, port):
    """Names ending in .example are 'public'; IP literals resolve to themselves."""
    return [PUBLIC_IP] if host.endswith(".example") else [host]


def use_mock_transport(monkeypatch, handler):
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )


def ok(request):
    return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>ok</p>")


@pytest.mark.parametrize(
    "location",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1/admin",
        "http://[::1]/",
        "file:///etc/passwd",
    ],
)
def test_redirect_to_internal_target_is_blocked(monkeypatch, location):
    seen = []

    def handler(request):
        seen.append(request.headers["host"])
        return httpx.Response(302, headers={"location": location})

    use_mock_transport(monkeypatch, handler)
    with pytest.raises(FetchError):
        fetch("http://public.example/", validator=make_validator(resolver))
    assert seen == ["public.example"]  # the internal address was never requested


def test_redirect_to_another_public_site_is_followed(monkeypatch):
    def handler(request):
        if request.headers["host"] == "public.example":
            return httpx.Response(302, headers={"location": "http://other.example/page"})
        return ok(request)

    use_mock_transport(monkeypatch, handler)
    page = fetch("http://public.example/", validator=make_validator(resolver))
    assert page.url == "http://other.example/page"
    assert "ok" in page.html


def test_connection_goes_to_the_address_that_was_checked(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.url.host, request.headers["host"], request.extensions))
        return ok(request)

    use_mock_transport(monkeypatch, handler)
    fetch("https://public.example/", validator=make_validator(resolver))
    [(connected_to, host_header, extensions)] = seen
    assert connected_to == PUBLIC_IP
    assert host_header == "public.example"
    assert extensions["sni_hostname"] == "public.example"


def test_dns_rebinding_cannot_change_the_address(monkeypatch):
    lookups = []
    connected = []

    def rebinding_resolver(host, port):
        lookups.append(host)
        return [PUBLIC_IP] if len(lookups) == 1 else ["127.0.0.1"]

    def handler(request):
        connected.append(request.url.host)
        return ok(request)

    use_mock_transport(monkeypatch, handler)
    fetch("http://evil.example/", validator=make_validator(rebinding_resolver))
    assert lookups == ["evil.example"]  # resolved once, never again
    assert connected == [PUBLIC_IP]


def test_ipv4_is_preferred_over_ipv6(monkeypatch):
    connected = []

    def handler(request):
        connected.append(request.url.host)
        return ok(request)

    use_mock_transport(monkeypatch, handler)
    both = make_validator(lambda host, port: [PUBLIC_IPV6, PUBLIC_IP])
    fetch("http://public.example/", validator=both)
    assert connected == [PUBLIC_IP]


def test_ipv6_only_host_works(monkeypatch):
    connected = []

    def handler(request):
        connected.append(request.url.host)
        return ok(request)

    use_mock_transport(monkeypatch, handler)
    fetch("http://public.example/", validator=make_validator(lambda host, port: [PUBLIC_IPV6]))
    assert connected == [PUBLIC_IPV6]


def test_validator_without_addresses_connects_directly(monkeypatch):
    connected = []

    def handler(request):
        connected.append(request.url.host)
        return ok(request)

    use_mock_transport(monkeypatch, handler)
    fetch("http://public.example/", validator=lambda url: None)
    assert connected == ["public.example"]


def test_pin_request_keeps_path_query_and_port():
    url, headers, extensions = pin_request(
        "http://public.example:443/a/b?x=1&y=2", [PUBLIC_IPV6, PUBLIC_IP]
    )
    assert url == f"http://{PUBLIC_IP}:443/a/b?x=1&y=2"
    assert headers == {"Host": "public.example:443"}
    assert extensions == {"sni_hostname": "public.example"}


def test_pin_request_brackets_ipv6_and_uses_punycode_names():
    url, headers, extensions = pin_request("https://m\u00fcnchen.example/", [PUBLIC_IPV6])
    assert url == f"https://[{PUBLIC_IPV6}]/"
    assert headers["Host"] == "xn--mnchen-3ya.example"
    assert extensions["sni_hostname"] == "xn--mnchen-3ya.example"
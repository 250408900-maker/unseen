"""Download a page with a timeout, a size cap, and manual redirect handling."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import httpx

from .detectors.base import Page

USER_AGENT = "unseen/0.1 (hidden-prompt scanner)"
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_BYTES = 2_000_000


class FetchError(Exception):
    """Raised when a page cannot be fetched safely."""


def check_url(url: str, validator: Callable[[str], None] | None = None) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError(f"Unsupported URL scheme: {parsed.scheme or 'none'}")
    if not parsed.hostname:
        raise FetchError("URL has no host")
    if validator is not None:
        validator(url)


def fetch(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    validator: Callable[[str], None] | None = None,
) -> Page:
    """Fetch url and return it as a Page. The validator runs on every hop, redirects included."""
    current = url
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    with httpx.Client(timeout=timeout, follow_redirects=False, headers=headers) as client:
        for _ in range(MAX_REDIRECTS + 1):
            check_url(current, validator)
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("Redirect without a Location header")
                        current = urljoin(current, location)
                        continue

                    if response.status_code >= 400:
                        raise FetchError(f"HTTP {response.status_code} from {current}")

                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and "html" not in content_type and "xml" not in content_type:
                        raise FetchError(f"Not an HTML page ({content_type})")

                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise FetchError(f"Page is larger than {max_bytes} bytes")

                    html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                    return Page.from_html(html, url=current)
            except httpx.HTTPError as exc:
                raise FetchError(f"Request failed: {exc}") from exc

    raise FetchError(f"Too many redirects (more than {MAX_REDIRECTS})")
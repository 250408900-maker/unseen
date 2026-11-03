"""HTTP API: the same scan as the CLI, over POST /scan."""

from __future__ import annotations

import ipaddress
import math
import os
import threading
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from unseen.cli import overall, scan_page
from unseen.detectors.base import Page, Severity
from unseen.fetcher import FetchError, fetch
from unseen.net_guard import make_validator
from unseen.ratelimit import RateLimiter
from unseen.render import RenderError, render_hidden_text
from unseen.sanitize import sanitize as sanitize_page

MAX_HTML_CHARS = 2_000_000
MAX_BODY_BYTES = 3_000_000

app = FastAPI(title="unseen", version="0.1.0")
RENDER_LOCK = threading.Lock()  # only one browser render at a time
URL_VALIDATOR = make_validator()  # SSRF guard: runs on the first URL and on every redirect

SCAN_LIMITER = RateLimiter(limit=10, window=60)  # scans per visitor per minute
RENDER_LIMITER = RateLimiter(limit=3, window=60)  # browser renders per visitor per minute

# Set UNSEEN_TRUST_PROXY=1 ONLY when a reverse proxy (Caddy) sits in front of the API.
# Otherwise visitors could fake X-Forwarded-For and dodge the rate limit.
TRUST_PROXY = os.environ.get("UNSEEN_TRUST_PROXY") == "1"


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "request body too large"}, status_code=413)
    return await call_next(request)


def client_key(http_request: Request) -> str:
    """The identity used for rate limiting: the visitor's IP (IPv6 grouped by /64)."""
    host = http_request.client.host if http_request.client else "unknown"
    if TRUST_PROXY:
        forwarded = http_request.headers.get("x-forwarded-for", "")
        if forwarded:
            host = forwarded.split(",")[-1].strip() or host  # the entry our proxy added
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    if isinstance(ip, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


class ScanRequest(BaseModel):
    url: str | None = None
    html: str | None = Field(default=None, max_length=MAX_HTML_CHARS)
    render: bool = False
    sanitize: bool = False
    min_severity: Literal["low", "medium", "high"] = "low"

    @model_validator(mode="after")
    def check_source(self) -> ScanRequest:
        if (self.url is None) == (self.html is None):
            raise ValueError("provide exactly one of 'url' or 'html'")
        if self.url is not None and not self.url.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return self


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scan")
def scan(request: ScanRequest, http_request: Request) -> dict:
    key = client_key(http_request)
    wait = SCAN_LIMITER.check(key)
    if wait == 0 and request.render:
        wait = RENDER_LIMITER.check(key)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail="too many requests, try again later",
            headers={"Retry-After": str(math.ceil(wait))},
        )

    if request.render and not RENDER_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="another render is running, try again soon")

    try:
        if request.url is not None:
            page = fetch(request.url, validator=URL_VALIDATOR)
        else:
            page = Page.from_html(request.html or "")
        if request.render:
            page.hidden_text = render_hidden_text(page.html)
    except FetchError as error:
        raise HTTPException(status_code=502, detail=f"could not fetch url: {error}") from error
    except RenderError as error:
        raise HTTPException(status_code=503, detail=f"rendering unavailable: {error}") from error
    finally:
        if request.render:
            RENDER_LOCK.release()

    merged = scan_page(page)
    top = overall(merged)
    minimum = Severity[request.min_severity.upper()]

    result: dict = {
        "target": request.url if request.url is not None else "(html)",
        "overall": top.name.lower() if top else None,
        "findings": [m.to_dict() for m in merged if m.severity >= minimum],
    }

    if request.sanitize:
        cleaned = sanitize_page(page)
        result["sanitized"] = {
            "text": cleaned.text,
            "removed": cleaned.removed,
            "comments_removed": cleaned.comments_removed,
            "invisible_removed": cleaned.invisible_removed,
        }

    return result
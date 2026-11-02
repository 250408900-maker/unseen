"""HTTP API: the same scan as the CLI, over POST /scan."""

from __future__ import annotations

import threading
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from unseen.cli import overall, scan_page
from unseen.detectors.base import Page, Severity
from unseen.fetcher import FetchError, fetch
from unseen.render import RenderError, render_hidden_text
from unseen.sanitize import sanitize as sanitize_page

MAX_HTML_CHARS = 2_000_000

app = FastAPI(title="unseen", version="0.1.0")
RENDER_LOCK = threading.Lock()  # only one browser render at a time


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
def scan(request: ScanRequest) -> dict:
    if request.render and not RENDER_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="another render is running, try again soon")

    try:
        if request.url is not None:
            page = fetch(request.url)
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
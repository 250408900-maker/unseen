"""Shared types and the base class every detector implements."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from bs4.element import Tag

if TYPE_CHECKING:
    from unseen.render import HiddenText


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def clip(text: str, limit: int = 120) -> str:
    """Collapse whitespace and shorten text for display."""
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def describe(tag: Tag) -> str:
    """Short CSS-like label for an element, e.g. div#note.footer."""
    label = tag.name
    if tag.get("id"):
        label += f"#{tag['id']}"
    classes = tag.get("class")
    if classes:
        label += "." + ".".join(classes)
    return label


@dataclass(frozen=True)
class Finding:
    detector: str
    severity: Severity
    message: str
    location: str
    snippet: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "detector": self.detector,
            "severity": self.severity.name.lower(),
            "message": self.message,
            "location": self.location,
            "snippet": self.snippet,
        }


@dataclass
class Page:
    url: str
    html: str
    soup: BeautifulSoup
    hidden_text: list[HiddenText] | None = None  # filled by render.py when --render is used

    @classmethod
    def from_html(cls, html: str, url: str = "") -> Page:
        return cls(url=url, html=html, soup=BeautifulSoup(html, "lxml"))


class Detector(ABC):
    """One hiding technique. Subclasses set name and description, then implement scan."""

    name: str
    description: str

    @abstractmethod
    def scan(self, page: Page) -> list[Finding]:
        """Return every finding for this technique on the page."""


REGISTRY: dict[str, type[Detector]] = {}


def register(cls: type[Detector]) -> type[Detector]:
    """Class decorator that adds a detector to the registry."""
    REGISTRY[cls.name] = cls
    return cls


def all_detectors() -> list[Detector]:
    return [cls() for cls in REGISTRY.values()]
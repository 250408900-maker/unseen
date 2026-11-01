"""Detector 4: text aimed at machines and assistive readers rather than at human eyes."""

from __future__ import annotations

from .base import Detector, Finding, Page, Severity, clip, describe, register
from .patterns import find_instruction

SKIP_ATTRS = {"href", "src", "srcset", "action", "style", "class", "id", "rel", "type", "name"}
LONG_ATTRS = {"alt", "title", "aria-label", "aria-description"}
MIN_LENGTH = 8
LONG_TEXT = 200


def attr_text(value: object) -> str:
    return " ".join(value) if isinstance(value, list) else str(value)


@register
class HiddenAttrs(Detector):
    name = "hidden_attrs"
    description = "Instructions in attributes, meta tags, noscript and aria-hidden content"

    def scan(self, page: Page) -> list[Finding]:
        findings: list[Finding] = []
        flagged: set[int] = set()

        def add(severity: Severity, message: str, location: str, snippet: str) -> None:
            findings.append(Finding(self.name, severity, message, location, snippet))

        for tag in page.soup.find_all(True):
            for attr, value in tag.attrs.items():
                if attr in SKIP_ATTRS:
                    continue
                text = attr_text(value)
                if len(text) < MIN_LENGTH:
                    continue
                location = f"{describe(tag)}[{attr}]"
                phrase = find_instruction(text)
                if phrase:
                    message = (
                        f'Attribute "{attr}" contains instruction-like text: '
                        f'"{clip(phrase, 60)}"'
                    )
                    add(Severity.HIGH, message, location, clip(text))
                elif attr in LONG_ATTRS and len(text) >= LONG_TEXT:
                    message = f'Unusually long "{attr}" text ({len(text)} characters)'
                    add(Severity.LOW, message, location, clip(text))

            if any(id(parent) in flagged for parent in tag.parents):
                continue

            if str(tag.get("aria-hidden", "")).lower() == "true":
                text = tag.get_text(" ", strip=True)
                phrase = find_instruction(text)
                if phrase:
                    flagged.add(id(tag))
                    message = (
                        "aria-hidden content contains instruction-like text: "
                        f'"{clip(phrase, 60)}"'
                    )
                    add(Severity.MEDIUM, message, describe(tag), clip(text))

            if tag.name == "noscript":
                text = tag.get_text(" ", strip=True)
                phrase = find_instruction(text)
                if phrase:
                    flagged.add(id(tag))
                    message = (
                        "noscript content contains instruction-like text: "
                        f'"{clip(phrase, 60)}"'
                    )
                    add(Severity.HIGH, message, describe(tag), clip(text))

        return findings
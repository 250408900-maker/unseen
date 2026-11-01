"""Detector 2: invisible Unicode characters, including hidden ASCII in tag characters."""

from __future__ import annotations

import re

from .base import Detector, Finding, Page, Severity, clip, describe, register

SKIP_TAGS = {"script", "style"}
BLACK_FLAG = "\U0001f3f4"

VARIATION = set(range(0xFE00, 0xFE10)) | set(range(0xE0100, 0xE01F0))
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0x180E, 0xFEFF, 0x2061, 0x2062, 0x2063, 0x2064}
PAYLOAD = "".join(chr(code) for code in sorted(VARIATION | ZERO_WIDTH))

TAG_RUN = re.compile("[\U000e0000-\U000e007f]+")
PAYLOAD_RUN = re.compile(f"[{PAYLOAD}]{{4,}}")
BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
LOW_NOISE = re.compile("[\u200b\u2060\u180e]")


def decode_tags(run: str) -> str:
    """Tag characters U+E0020..U+E007E mirror ASCII 0x20..0x7E."""
    chars = []
    for char in run:
        code = ord(char) - 0xE0000
        if 0x20 <= code <= 0x7E:
            chars.append(chr(code))
    return "".join(chars)


def scan_text(text: str, location: str, name: str) -> list[Finding]:
    findings: list[Finding] = []

    def add(severity: Severity, message: str, snippet: str = "") -> None:
        findings.append(Finding(name, severity, message, location, snippet))

    for match in TAG_RUN.finditer(text):
        run = match.group()
        before = text[match.start() - 1 : match.start()]
        if before == BLACK_FLAG and len(run) <= 8:
            continue  # subdivision flag emoji such as England or Scotland
        add(
            Severity.HIGH,
            f"{len(run)} Unicode tag characters carry hidden ASCII",
            f'decoded: "{clip(decode_tags(run))}"',
        )

    for match in PAYLOAD_RUN.finditer(text):
        run = match.group()
        codes = " ".join(f"U+{ord(char):04X}" for char in run[:6])
        add(
            Severity.HIGH,
            f"{len(run)} invisible characters in a row (possible encoded data)",
            codes,
        )

    if BIDI.search(text):
        count = len(BIDI.findall(text))
        add(
            Severity.MEDIUM,
            "Bidirectional control characters can reorder displayed text",
            f"count: {count}",
        )

    if not any(f.severity == Severity.HIGH for f in findings):
        count = len(LOW_NOISE.findall(text))
        if count:
            add(Severity.LOW, "Zero-width characters in text", f"count: {count}")

    return findings


@register
class InvisibleUnicode(Detector):
    name = "invisible_unicode"
    description = "Invisible Unicode characters that can hide or encode text"

    def scan(self, page: Page) -> list[Finding]:
        findings: list[Finding] = []

        for node in page.soup.find_all(string=True):
            parent = node.parent
            if parent is None or parent.name in SKIP_TAGS:
                continue
            findings.extend(scan_text(str(node), describe(parent), self.name))

        for tag in page.soup.find_all(True):
            for attr, value in tag.attrs.items():
                text = " ".join(value) if isinstance(value, list) else str(value)
                findings.extend(scan_text(text, f"{describe(tag)}[{attr}]", self.name))

        return findings
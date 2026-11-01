"""Detector 1: text hidden from humans with CSS or the hidden attribute."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from .base import Detector, Finding, Page, Severity, clip, describe, register

SKIP_TAGS = {"script", "style", "noscript", "template", "head", "title", "meta", "link"}

# Common on legitimate pages (menus, modals), so they score lower than deceptive tricks.
ORDINARY = {"hidden attribute", "display:none", "visibility:hidden"}

NAMED_COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
}

COLOR_RE = re.compile(
    r"#[0-9a-f]{6}\b|#[0-9a-f]{3}\b|rgba?\([^)]*\)|\b(?:" + "|".join(NAMED_COLORS) + r")\b"
)
RULE_RE = re.compile(r"([^{}@]+)\{([^{}]*)\}")
CLIP_RECT_RE = re.compile(r"rect\(\s*0(?:px)?[\s,]+0(?:px)?[\s,]+0(?:px)?[\s,]+0(?:px)?\s*\)")
TRANSPARENT_RE = re.compile(r"rgba\(\d+,\d+,\d+,0(?:\.0+)?\)")


def number(value: str) -> float | None:
    match = re.match(r"\s*(-?\d*\.?\d+)", value)
    return float(match.group(1)) if match else None


def parse_color(value: str) -> tuple[int, ...] | None:
    value = value.strip().lower().replace(" ", "")
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", value)
    if match:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))
    match = re.fullmatch(r"rgba?\((\d+),(\d+),(\d+)(?:,[\d.]+)?\)", value)
    if match:
        return tuple(int(g) for g in match.groups())
    return None


def find_color(value: str) -> tuple[int, ...] | None:
    match = COLOR_RE.search(value.lower())
    return parse_color(match.group(0)) if match else None


def is_transparent(value: str) -> bool:
    value = value.replace(" ", "")
    return value == "transparent" or bool(TRANSPARENT_RE.fullmatch(value))


def parse_declarations(block: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for part in block.split(";"):
        if ":" not in part:
            continue
        prop, _, value = part.partition(":")
        value = re.sub(r"\s*!important\s*$", "", value.strip(), flags=re.I)
        declarations[prop.strip().lower()] = value.lower()
    return declarations


def compute_styles(soup: BeautifulSoup) -> dict[int, dict[str, str]]:
    """Map id(tag) to declarations from <style> blocks. Specificity is ignored (last rule wins)."""
    css = "\n".join(style.get_text() for style in soup.find_all("style"))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    styles: dict[int, dict[str, str]] = {}
    for selector, body in RULE_RE.findall(css):
        try:
            matches = soup.select(selector.strip())
        except Exception:
            continue
        declarations = parse_declarations(body)
        for tag in matches:
            styles.setdefault(id(tag), {}).update(declarations)
    return styles


def hiding_reasons(tag: Tag, style: dict[str, str]) -> list[str]:
    reasons: list[str] = []

    if tag.has_attr("hidden"):
        reasons.append("hidden attribute")
    if style.get("display") == "none":
        reasons.append("display:none")
    if style.get("visibility") in ("hidden", "collapse"):
        reasons.append("visibility:hidden")

    opacity = number(style.get("opacity", ""))
    if opacity is not None and opacity <= 0.01:
        reasons.append("opacity:0")

    font_size = number(style.get("font-size", ""))
    if font_size is not None and (font_size == 0 or (font_size <= 1 and "px" in style["font-size"])):
        reasons.append("font-size:0")

    indent = number(style.get("text-indent", ""))
    if indent is not None and indent <= -500:
        reasons.append("text-indent off-screen")

    if style.get("position") in ("absolute", "fixed", "relative"):
        for side in ("left", "top", "right", "bottom"):
            offset = number(style.get(side, ""))
            if offset is not None and offset <= -500:
                reasons.append("off-screen position")
                break

    clip_value = style.get("clip", "").replace(" ", "")
    clip_path = style.get("clip-path", "").replace(" ", "")
    if CLIP_RECT_RE.fullmatch(style.get("clip", "").strip()) or clip_value == "rect(0,0,0,0)":
        reasons.append("clipped to nothing")
    elif clip_path.startswith(("inset(100%", "inset(50%")):
        reasons.append("clipped to nothing")

    if style.get("overflow") == "hidden":
        width = number(style.get("width", ""))
        height = number(style.get("height", ""))
        if (width is not None and width <= 1) or (height is not None and height <= 1):
            reasons.append("zero-size container")

    color = style.get("color", "")
    if color and is_transparent(color):
        reasons.append("transparent text")
    else:
        fg = find_color(color) if color else None
        bg_value = style.get("background-color") or style.get("background") or ""
        bg = find_color(bg_value) if bg_value else None
        if fg is not None and fg == bg:
            reasons.append("text color equals background")

    return reasons


@register
class CssHiding(Detector):
    name = "css_hiding"
    description = "Text hidden from humans with CSS or the hidden attribute"

    def scan(self, page: Page) -> list[Finding]:
        styles = compute_styles(page.soup)
        findings: list[Finding] = []
        flagged: set[int] = set()

        for tag in page.soup.find_all(True):
            if tag.name in SKIP_TAGS:
                continue
            if any(id(parent) in flagged for parent in tag.parents):
                continue

            style = dict(styles.get(id(tag), {}))
            style.update(parse_declarations(tag.get("style", "") or ""))

            reasons = hiding_reasons(tag, style)
            if not reasons:
                continue

            text = tag.get_text(" ", strip=True)
            if not text:
                continue

            flagged.add(id(tag))
            deceptive = [r for r in reasons if r not in ORDINARY]
            if deceptive:
                severity = Severity.HIGH if len(text) >= 20 else Severity.MEDIUM
            else:
                severity = Severity.LOW

            findings.append(
                Finding(
                    detector=self.name,
                    severity=severity,
                    message=f"Hidden from humans via {', '.join(reasons)}",
                    location=describe(tag),
                    snippet=clip(text),
                )
            )
        return findings
"""Produce a cleaned text version of a page with hidden content removed."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag

from unseen.detectors.base import Page, describe
from unseen.detectors.css_hiding import (
    SKIP_TAGS,
    compute_styles,
    hiding_reasons,
    parse_declarations,
)
from unseen.detectors.invisible_unicode import BIDI, PAYLOAD_RUN
from unseen.detectors.patterns import INVISIBLE, find_instruction

BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "main", "nav", "aside",
    "ul", "ol", "li", "dl", "dt", "dd", "table", "tr", "blockquote", "pre", "form",
    "fieldset", "figure", "figcaption", "h1", "h2", "h3", "h4", "h5", "h6",
}  # fmt: skip


@dataclass(frozen=True)
class SanitizeResult:
    text: str
    removed: list[str]  # hidden elements that held text, e.g. "div: display:none"
    comments_removed: int
    invisible_removed: int  # invisible characters stripped from the text


def hidden_reasons(tag: Tag, styles: dict[int, dict[str, str]]) -> list[str]:
    style = dict(styles.get(id(tag), {}))
    style.update(parse_declarations(tag.get("style", "") or ""))
    reasons = hiding_reasons(tag, style)
    if str(tag.get("aria-hidden", "")).lower() == "true":
        if find_instruction(tag.get_text(" ", strip=True)):
            reasons.append("aria-hidden with instruction-like text")
    return reasons


def sanitize(page: Page) -> SanitizeResult:
    """Return the page text with hidden elements, comments and invisible characters removed."""
    soup = BeautifulSoup(page.html, "lxml")  # fresh copy: the page's own soup is not touched
    styles = compute_styles(soup)

    marked: set[int] = set()
    doomed: list[Tag] = []
    removed: list[str] = []

    for tag in soup.find_all(True):
        if any(id(parent) in marked for parent in tag.parents):
            continue
        if tag.name in SKIP_TAGS:
            marked.add(id(tag))
            doomed.append(tag)
            continue
        reasons = hidden_reasons(tag, styles)
        if not reasons:
            continue
        marked.add(id(tag))
        doomed.append(tag)
        if tag.get_text(" ", strip=True):
            removed.append(f"{describe(tag)}: {', '.join(reasons)}")

    for tag in doomed:
        tag.decompose()

    comments = soup.find_all(string=lambda s: isinstance(s, Comment))
    for comment in comments:
        comment.extract()

    for tag in soup.find_all(True):
        if tag.name == "br":
            tag.replace_with(NavigableString("\n"))
        elif tag.name in BLOCK_TAGS:
            tag.insert(0, NavigableString("\n"))
            tag.append(NavigableString("\n"))

    text = soup.get_text()

    before = len(text)
    for pattern in (PAYLOAD_RUN, INVISIBLE, BIDI):
        text = pattern.sub("", text)
    invisible_removed = before - len(text)

    lines = [re.sub(r"[ \t\r\f\v\xa0]+", " ", line).strip() for line in text.split("\n")]
    cleaned: list[str] = []
    for line in lines:
        if line or (cleaned and cleaned[-1]):
            cleaned.append(line)

    return SanitizeResult(
        text="\n".join(cleaned).strip(),
        removed=removed,
        comments_removed=len(comments),
        invisible_removed=invisible_removed,
    )
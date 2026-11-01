"""Shared heuristics: does a piece of text look like instructions aimed at an AI model?"""

from __future__ import annotations

import re
import unicodedata

# Zero-width, bidi-control, soft-hyphen, BOM and Unicode tag characters.
INVISIBLE = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u00ad\ufeff"
    "\U000e0000-\U000e007f]"
)

_SOURCES = [
    # Override earlier instructions: "ignore all previous instructions"
    (
        r"\b(?:ignore|disregard|forget|override|bypass)\b(?:\s+\w+){0,3}?\s+"
        r"(?:previous|prior|above|earlier|preceding|system|original)\s+"
        r"(?:instructions?|prompts?|rules?|context|messages?|guidelines?|directions?)"
    ),
    # Persona or mode switch: "you are now in developer mode"
    (
        r"\byou\s+are\s+now\s+(?:in\s+(?:\w+\s+){0,2}mode\b"
        r"|(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken|evil)\b"
        r"|(?:acting|playing|roleplaying)\b|going\s+to\b)"
    ),
    r"\b(?:developer|admin|debug|god|sudo|dan|jailbreak)\s+mode\b",
    r"\bpretend\s+(?:to\s+be|you\s+are|that\s+you)\b",
    # Addressing the model directly: "note to AI assistants"
    (
        r"\b(?:note|message|attention|notice|instructions?)\s+(?:to|for)\s+(?:the\s+)?"
        r"(?:ai|llm|language\s+model|chat\s?bot|assistant|agent|bot|model)s?"
        r"(?:\s+(?:assistant|agent|model|system)s?)?\b"
    ),
    (
        r"\bif\s+you(?:'re|\s+are)\s+(?:an?\s+)?"
        r"(?:ai|llm|language\s+model|chat\s?bot|artificial\s+intelligence)\b"
    ),
    # Secrecy: "do not tell the user"
    (
        r"\b(?:do\s+not|don't|never)\s+(?:tell|inform|mention|reveal|disclose|alert|notify)"
        r"\s+(?:this\s+to\s+)?(?:the\s+)?(?:user|human|person)\b"
    ),
    # Prompt extraction
    (
        r"\b(?:reveal|print|repeat|output|show|disclose|leak)\b[^.\n]{0,30}?"
        r"\b(?:system\s+prompt|hidden\s+prompt|your\s+instructions)\b"
    ),
    # Fake prompt structure
    r"\bnew\s+(?:instructions?|system\s+prompt|rules)\s*[:\-]",
    r"\bsystem\s*(?:prompt|message)\s*[:\-]",
    r"<\|?(?:im_start|im_end|system|endoftext)\|?>|\[/?inst\]|<<sys>>",
    # Exfiltration: a verb, then something sensitive, then an address or URL
    (
        r"\b(?:send|forward|email|post|upload|leak|transmit|exfiltrate)\b[^.\n]{0,60}?"
        r"\b(?:conversations?|chats?|history|data|credentials?|passwords?|cookies?|tokens?"
        r"|secrets?|files?|contents?|information|details)\b[^.\n]{0,60}?"
        r"(?:https?://\S+|[\w.+-]+@[\w-]+\.[\w.-]+)"
    ),
]

PATTERNS = [re.compile(source, re.IGNORECASE) for source in _SOURCES]


def normalize(text: str) -> str:
    """Fold lookalike characters, drop invisible ones, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = INVISIBLE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def find_instruction(text: str) -> str | None:
    """Return the earliest instruction-like phrase in text, or None."""
    text = normalize(text)
    matches = [m for pattern in PATTERNS if (m := pattern.search(text))]
    if not matches:
        return None
    best = min(matches, key=lambda m: (m.start(), -len(m.group(0))))
    return best.group(0)


def looks_like_instruction(text: str) -> bool:
    return find_instruction(text) is not None
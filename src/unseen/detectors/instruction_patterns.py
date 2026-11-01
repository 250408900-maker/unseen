"""Detector 5: Suspicious AI-directed instruction patterns."""

import re
from dataclasses import dataclass

from bs4.element import Comment

from .base import Detector, Finding, Page, Severity, clip, describe, register
from .patterns import normalize

MODE_NAMES = (
    r"developer|admin|administrator|debug|god|sudo|dan|jailbreak|unrestricted|unfiltered"
)
UNSAFE_PERSONAS = r"unrestricted|unfiltered|jailbroken|uncensored"
DESTINATION = r"\b(?:to|at)\s+(?:https?://\S+|[\w.+-]+@[\w-]+\.[\w.-]+)"

PATTERNS = {
    "instruction_override": [
        r"\bignore (?:all |any )?(?:previous|prior|above) instructions\b",
        r"\bdisregard (?:previous|prior|all) instructions\b",
        r"\bforget (?:all |your )?(?:previous|prior) instructions\b",
    ],
    "role_spoofing": [
        rf"\byou are now (?:in )?(?:{MODE_NAMES}) mode\b",
        rf"\byou are now (?:an? )?(?:{UNSAFE_PERSONAS}|evil)\b",
        rf"\bact as (?:an? )?(?:{UNSAFE_PERSONAS}|system administrator)\b",
        r"\bsystem (?:message|prompt|instruction)\s*:",
    ],
    "secret_extraction": [
        r"\breveal (?:your |the )?(?:system prompt|secret|api key)\b",
        r"\b(?:send|upload|forward|exfiltrate)\b[^.\n]{0,80}"
        r"\b(?:token|password|api key|credentials|secret)s?\b[^.\n]{0,60}" + DESTINATION,
    ],
    "concealment": [
        r"\bdo not (?:tell|inform|notify) the user\b",
        r"\bkeep (?:this|these instructions) secret\b",
        r"\bwithout (?:the user's|user) knowledge\b",
    ],
}

COMPILED_PATTERNS = {
    category: [re.compile(p, re.IGNORECASE) for p in expressions]
    for category, expressions in PATTERNS.items()
}

SKIPPED_PARENTS = {"script", "style"}


@dataclass
class InstructionMatch:
    category: str
    text: str
    severity: str
    start: int
    end: int


def detect_instruction_patterns(text: str) -> list[InstructionMatch]:
    """Detect suspicious AI-directed instructions in text (after normalization)."""
    text = normalize(text)
    findings = []
    seen = set()

    for category, expressions in COMPILED_PATTERNS.items():
        for expression in expressions:
            for match in expression.finditer(text):
                key = (category, match.start(), match.end())

                if key in seen:
                    continue

                seen.add(key)

                findings.append(
                    InstructionMatch(
                        category=category,
                        text=match.group(0),
                        severity=(
                            "high"
                            if category in {
                                "instruction_override",
                                "secret_extraction",
                            }
                            else "medium"
                        ),
                        start=match.start(),
                        end=match.end(),
                    )
                )

    return sorted(findings, key=lambda item: item.start)


@register
class InstructionPatterns(Detector):
    name = "instruction_patterns"
    description = "Text aimed at AI models, such as 'ignore previous instructions'"

    def scan(self, page: Page) -> list[Finding]:
        findings: list[Finding] = []

        for node in page.soup.find_all(string=True):
            text = str(node).strip()
            if not text:
                continue

            parent = node.parent
            if parent is not None and parent.name in SKIPPED_PARENTS:
                continue

            is_comment = isinstance(node, Comment)
            severity = Severity.HIGH if is_comment else Severity.MEDIUM
            where = "comment" if is_comment else "text"

            if parent is None:
                location = where
            elif is_comment:
                location = f"comment in {describe(parent)}"
            else:
                location = describe(parent)

            for match in detect_instruction_patterns(text):
                label = match.category.replace("_", " ").capitalize()
                findings.append(
                    Finding(
                        detector=self.name,
                        severity=severity,
                        message=f'{label} phrase in {where}: "{clip(match.text, 60)}"',
                        location=location,
                        snippet=clip(text),
                    )
                )

        return findings
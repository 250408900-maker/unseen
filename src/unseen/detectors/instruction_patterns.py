
"""Detector 5: Suspicious AI-directed instruction patterns."""

import re
from dataclasses import dataclass
from html.parser import HTMLParser

PATTERNS = {
    "instruction_override": [
        r"\bignore (?:all |any )?(?:previous|prior|above) instructions\b",
        r"\bdisregard (?:previous|prior|all) instructions\b",
        r"\bforget (?:all |your )?(?:previous|prior) instructions\b",
    ],
    "role_spoofing": [
        r"\byou are now (?:a |an )?\w+",
        r"\bact as (?:a |an )?\w+",
        r"\bsystem (?:message|prompt|instruction)\s*:",
    ],
    "secret_extraction": [
        r"\breveal (?:your |the )?(?:system prompt|secret|api key)\b",
        r"\b(?:send|upload|forward|exfiltrate)\b.{0,100}"
        r"\b(?:token|password|api key|credentials|secret)\b",
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


@dataclass
class InstructionMatch:
    category: str
    text: str
    severity: str
    start: int
    end: int


def detect_instruction_patterns(text: str) -> list[InstructionMatch]:
    """Detect suspicious AI-directed instructions in text."""
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


class TextExtractor(HTMLParser):
    """Extract text from HTML, including hidden elements."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_comment(self, data):
        self.parts.append(data)


def scan_html(html: str) -> list[InstructionMatch]:
    """Scan HTML text and comments for instruction patterns."""
    parser = TextExtractor()
    parser.feed(html)
    return detect_instruction_patterns("\n".join(parser.parts))

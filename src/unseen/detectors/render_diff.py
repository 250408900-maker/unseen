"""Detector 6: text that is in the page but not visible when a browser renders it."""

from __future__ import annotations

from .base import Detector, Finding, Page, Severity, clip, register
from .css_hiding import ORDINARY


@register
class RenderDiff(Detector):
    name = "render_diff"
    description = "Text that a browser renders invisibly (needs --render)"

    def scan(self, page: Page) -> list[Finding]:
        if page.hidden_text is None:  # page was not rendered
            return []

        findings: list[Finding] = []
        for item in page.hidden_text:
            deceptive = [reason for reason in item.reasons if reason not in ORDINARY]
            if deceptive:
                severity = Severity.HIGH if len(item.text) >= 20 else Severity.MEDIUM
            else:
                severity = Severity.LOW

            findings.append(
                Finding(
                    detector=self.name,
                    severity=severity,
                    message=f"Invisible when rendered in a browser: {', '.join(item.reasons)}",
                    location=item.location,
                    snippet=clip(item.text),
                )
            )
        return findings
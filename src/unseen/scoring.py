"""Merge findings from all detectors into one result per location."""

from __future__ import annotations

from dataclasses import dataclass

from unseen.detectors.base import Finding, Severity


@dataclass(frozen=True)
class MergedFinding:
    location: str
    severity: Severity
    detectors: tuple[str, ...]
    messages: tuple[str, ...]
    snippet: str

    def to_dict(self) -> dict:
        return {
            "location": self.location,
            "severity": self.severity.name.lower(),
            "detectors": list(self.detectors),
            "messages": list(self.messages),
            "snippet": self.snippet,
        }


def merge_findings(findings: list[Finding]) -> list[MergedFinding]:
    """Group findings by location, keep the top severity, list every detector.

    If a hiding detector and instruction_patterns both fire on the same
    location, the severity is raised to HIGH.
    """
    groups: dict[str, list[Finding]] = {}
    for finding in findings:
        groups.setdefault(finding.location, []).append(finding)

    merged = []
    for location, group in groups.items():
        detectors = tuple(sorted({f.detector for f in group}))
        messages = tuple(dict.fromkeys(f.message for f in group))
        top = max(group, key=lambda f: f.severity)
        severity = top.severity

        has_instruction = "instruction_patterns" in detectors
        has_hiding = any(name != "instruction_patterns" for name in detectors)
        if has_instruction and has_hiding:
            severity = Severity.HIGH

        merged.append(
            MergedFinding(
                location=location,
                severity=severity,
                detectors=detectors,
                messages=messages,
                snippet=top.snippet,
            )
        )

    return sorted(merged, key=lambda m: (-m.severity, m.location))


def overall_severity(findings: list[Finding]) -> Severity | None:
    """Highest severity across all findings, or None for a clean page."""
    return max((f.severity for f in findings), default=None)
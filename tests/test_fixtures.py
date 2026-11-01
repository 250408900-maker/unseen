"""Run every fixture through the real scanner and check it against expected.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unseen.cli import scan_target
from unseen.detectors.base import Severity

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def severity(name: str) -> Severity:
    return Severity[name.upper()]


def scan(relative: str):
    return scan_target(str(FIXTURES / relative))


@pytest.mark.parametrize("entry", MANIFEST["poisoned"], ids=lambda e: Path(e["file"]).stem)
def test_poisoned_fixture_is_detected(entry):
    merged = scan(entry["file"])
    minimum = severity(entry["min_severity"])
    for detector in entry["detectors"]:
        hits = [m for m in merged if detector in m.detectors and m.severity >= minimum]
        assert hits, f"{detector} did not report {minimum.name} or higher on {entry['file']}"


@pytest.mark.parametrize("entry", MANIFEST["clean"], ids=lambda e: Path(e["file"]).stem)
def test_clean_fixture_is_not_flagged(entry):
    merged = scan(entry["file"])
    if entry["max_severity"] == "none":
        flagged = merged
    else:
        limit = severity(entry["max_severity"])
        flagged = [m for m in merged if m.severity > limit]
    details = ", ".join(f"{m.severity.name} {m.location}" for m in flagged)
    assert not flagged, f"{entry['file']} was flagged above {entry['max_severity']}: {details}"


def test_manifest_lists_every_fixture_file():
    on_disk = {
        path.relative_to(FIXTURES).as_posix()
        for folder in ("poisoned", "clean")
        for path in (FIXTURES / folder).glob("*.html")
    }
    listed = {entry["file"] for group in MANIFEST.values() for entry in group}
    assert on_disk == listed


def test_hiding_plus_instruction_merges_to_high():
    merged = scan("poisoned/combo_display_none_instruction.html")
    assert any(
        {"css_hiding", "instruction_patterns"} <= set(m.detectors) and m.severity == Severity.HIGH
        for m in merged
    )
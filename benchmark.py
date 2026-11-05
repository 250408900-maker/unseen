"""Run every fixture and report detection rate, false positives and a per-detector table.

Run from the project root:  python benchmark.py
Exit code 1 if any fixture misses its expectation.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from unseen.cli import overall, scan_page
from unseen.detectors.base import Page, Severity

FIXTURES = Path(__file__).parent / "tests" / "fixtures"


def scan_file(relative: str):
    html = (FIXTURES / relative).read_text(encoding="utf-8")
    return scan_page(Page.from_html(html))


def main() -> int:
    manifest = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    detected = 0
    per_detector: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [caught, total]

    for item in manifest["poisoned"]:
        merged = scan_file(item["file"])
        minimum = Severity[item["min_severity"].upper()]
        fired = {name for finding in merged for name in finding.detectors}
        top = overall(merged)
        ok = top is not None and top >= minimum

        for name in item["detectors"]:
            per_detector[name][1] += 1
            if name in fired:
                per_detector[name][0] += 1
            else:
                ok = False

        if ok:
            detected += 1
        else:
            failures.append(f"MISSED  {item['file']} (expected {item['detectors']} >= {item['min_severity']})")

    false_positives = 0
    for item in manifest["clean"]:
        top = overall(scan_file(item["file"]))
        allowed = item["max_severity"]
        limit = None if allowed == "none" else Severity[allowed.upper()]
        too_loud = top is not None and (limit is None or top > limit)
        if too_loud:
            false_positives += 1
            failures.append(f"FALSE POSITIVE  {item['file']} ({top.name.lower()}, allowed {allowed})")

    poisoned_total = len(manifest["poisoned"])
    clean_total = len(manifest["clean"])

    print("unseen benchmark")
    print("-" * 44)
    print(f"Poisoned fixtures detected : {detected}/{poisoned_total}")
    print(f"Clean fixtures flagged     : {false_positives}/{clean_total}")
    print()
    print(f"{'Detector':<22}{'Caught':>8}{'Total':>8}")
    for name in sorted(per_detector):
        caught, total = per_detector[name]
        print(f"{name:<22}{caught:>8}{total:>8}")

    if failures:
        print()
        for line in failures:
            print(line)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""Command line interface: scan a URL or local HTML file."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import unseen.detectors  # noqa: F401  (registers all detectors)
from unseen.detectors.base import Page, Severity, all_detectors
from unseen.scoring import merge_findings, overall_severity

EXIT_CLEAN = 0
EXIT_FOUND = 1
EXIT_ERROR = 2


def load_html(target: str) -> tuple[str, str]:
    """Return (html, url) for a URL or a local file path."""
    if target.startswith(("http://", "https://")):
        request = urllib.request.Request(target, headers={"User-Agent": "unseen/0.1"})
        with urllib.request.urlopen(request, timeout=15) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace"), target
    path = Path(target)
    return path.read_text(encoding="utf-8", errors="replace"), str(path)


def scan_target(target: str):
    html, url = load_html(target)
    page = Page.from_html(html, url=url)
    findings = []
    for detector in all_detectors():
        findings.extend(detector.scan(page))
    return findings


def print_report(target: str, findings) -> None:
    merged = merge_findings(findings)
    top = overall_severity(findings)
    print(f"unseen scan: {target}")
    if not merged:
        print("No hidden content found.")
        return
    print(f"Overall severity: {top.name}  ({len(merged)} locations)\n")
    for item in merged:
        print(f"[{item.severity.name}] {item.location}")
        print(f"    detectors: {', '.join(item.detectors)}")
        for message in item.messages:
            print(f"    - {message}")
        if item.snippet:
            print(f"    snippet: {item.snippet}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="unseen",
        description="Find hidden text on a web page that humans cannot see but AI models can.",
    )
    parser.add_argument("target", help="URL or path to an HTML file")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    parser.add_argument(
        "--min-severity",
        choices=["low", "medium", "high"],
        default="low",
        help="only report findings at or above this level",
    )
    args = parser.parse_args(argv)

    try:
        findings = scan_target(args.target)
    except Exception as error:  # network, file, or decoding problems
        print(f"unseen: could not scan {args.target}: {error}", file=sys.stderr)
        return EXIT_ERROR

    minimum = Severity[args.min_severity.upper()]
    findings = [f for f in findings if f.severity >= minimum]

    if args.json:
        output = {
            "target": args.target,
            "overall": overall_severity(findings).name.lower() if findings else None,
            "findings": [m.to_dict() for m in merge_findings(findings)],
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(args.target, findings)

    return EXIT_FOUND if findings else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
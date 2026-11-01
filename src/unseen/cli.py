"""Command line interface: scan a URL or local HTML file."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import unseen.detectors  # noqa: F401  (registers all detectors)
from unseen.detectors.base import Page, Severity, all_detectors
from unseen.scoring import MergedFinding, merge_findings

EXIT_OK = 0
EXIT_RISK = 1
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


def scan_target(target: str) -> list[MergedFinding]:
    html, url = load_html(target)
    page = Page.from_html(html, url=url)
    findings = []
    for detector in all_detectors():
        findings.extend(detector.scan(page))
    return merge_findings(findings)


def overall(merged: list[MergedFinding]) -> Severity | None:
    return max((m.severity for m in merged), default=None)


def print_report(target: str, merged: list[MergedFinding]) -> None:
    print(f"unseen scan: {target}")
    top = overall(merged)
    if top is None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unseen",
        description="Find hidden text on a web page that humans cannot see but AI models can.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="scan a URL or an HTML file")
    scan.add_argument("target", help="URL or path to an HTML file")
    scan.add_argument("--json", action="store_true", help="print results as JSON")
    scan.add_argument(
        "--min-severity",
        choices=["low", "medium", "high"],
        default="low",
        help="only show findings at or above this level",
    )
    scan.add_argument(
        "--fail-on",
        choices=["low", "medium", "high"],
        default="high",
        help="exit with code 1 if any finding is at or above this level (default: high)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        merged = scan_target(args.target)
    except Exception as error:  # network, file, or decoding problems
        print(f"unseen: could not scan {args.target}: {error}", file=sys.stderr)
        return EXIT_ERROR

    fail_level = Severity[args.fail_on.upper()]
    top = overall(merged)
    failed = top is not None and top >= fail_level

    shown = [m for m in merged if m.severity >= Severity[args.min_severity.upper()]]

    if args.json:
        output = {
            "target": args.target,
            "overall": top.name.lower() if top else None,
            "findings": [m.to_dict() for m in shown],
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(args.target, shown)

    return EXIT_RISK if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
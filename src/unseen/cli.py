from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import unseen.detectors  # noqa: F401  (registers all detectors)
from unseen.detectors.base import Page, Severity, all_detectors
from unseen.fetcher import FetchError, fetch
from unseen.report import render as print_report
from unseen.sanitize import sanitize
from unseen.scoring import MergedFinding, merge_findings

EXIT_OK = 0
EXIT_RISK = 1
EXIT_ERROR = 2


def load_page(target: str) -> Page:
    """Return a Page for a URL (via fetcher.py) or a local file path."""
    if target.startswith(("http://", "https://")):
        return fetch(target)
    path = Path(target)
    html = path.read_text(encoding="utf-8", errors="replace")
    return Page.from_html(html, url=str(path))


def scan_page(page: Page) -> list[MergedFinding]:
    findings = []
    for detector in all_detectors():
        findings.extend(detector.scan(page))
    return merge_findings(findings)


def scan_target(target: str) -> list[MergedFinding]:
    return scan_page(load_page(target))


def overall(merged: list[MergedFinding]) -> Severity | None:
    return max((m.severity for m in merged), default=None)


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
    scan.add_argument(
        "--sanitize",
        metavar="FILE",
        help="write a cleaned text version of the page (hidden content removed) to FILE",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        page = load_page(args.target)
        merged = scan_page(page)
        cleaned = sanitize(page) if args.sanitize else None
    except FetchError as error:
        print(f"unseen: could not fetch {args.target}: {error}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as error:  # file or decoding problems
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

    if cleaned is not None:
        try:
            Path(args.sanitize).write_text(cleaned.text + "\n", encoding="utf-8")
        except OSError as error:
            print(f"unseen: could not write {args.sanitize}: {error}", file=sys.stderr)
            return EXIT_ERROR
        print(
            f"unseen: cleaned text written to {args.sanitize} "
            f"({len(cleaned.removed)} hidden elements, {cleaned.comments_removed} comments, "
            f"{cleaned.invisible_removed} invisible characters removed)",
            file=sys.stderr,
        )

    return EXIT_RISK if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
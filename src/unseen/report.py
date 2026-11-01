"""Terminal report for scan results, rendered with rich."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from unseen.detectors.base import Severity
from unseen.scoring import MergedFinding

STYLES = {
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "bold yellow",
    Severity.LOW: "bold cyan",
}


def label(severity: Severity) -> Text:
    return Text(f"[{severity.name}]", style=STYLES[severity])


def render(target: str, merged: list[MergedFinding], console: Console | None = None) -> None:
    """Print a scan report. The console is created at call time so output can be captured."""
    console = console or Console()

    def out(text: Text | str = "") -> None:
        console.print(text, soft_wrap=True, highlight=False, markup=False)

    out(f"unseen scan: {target}")

    if not merged:
        out(Text("No hidden content found.", style="green"))
        return

    top = max(item.severity for item in merged)
    count = f"  ({len(merged)} locations)"
    out(Text.assemble("Overall severity: ", (top.name, STYLES[top]), count))
    out()

    for item in merged:
        out(Text.assemble(label(item.severity), " ", (item.location, "bold")))
        out(Text(f"    detectors: {', '.join(item.detectors)}", style="dim"))
        for message in item.messages:
            out(f"    - {message}")
        if item.snippet:
            out(Text(f"    snippet: {item.snippet}", style="dim"))
        out()
from unseen.detectors.base import Page, Severity
from unseen.detectors.css_hiding import CssHiding
from unseen.detectors.render_diff import RenderDiff
from unseen.render import HiddenText
from unseen.scoring import merge_findings


def scan(hidden):
    page = Page.from_html("<p>x</p>")
    page.hidden_text = hidden
    return RenderDiff().scan(page)


def test_not_rendered_gives_no_findings():
    assert scan(None) == []


def test_ordinary_hiding_is_low():
    [finding] = scan([HiddenText("div", ["display:none"], "menu")])
    assert finding.severity == Severity.LOW


def test_short_deceptive_hiding_is_medium():
    [finding] = scan([HiddenText("div", ["off-screen position"], "short")])
    assert finding.severity == Severity.MEDIUM


def test_long_deceptive_hiding_is_high():
    text = "this hidden text is long enough"
    [finding] = scan([HiddenText("div", ["font-size:0"], text)])
    assert finding.severity == Severity.HIGH


def test_location_and_snippet_are_kept():
    [finding] = scan([HiddenText("p.note", ["opacity:0"], "secret")])
    assert finding.location == "p.note"
    assert finding.snippet == "secret"
    assert finding.detector == "render_diff"


def test_merges_with_css_hiding_on_same_element():
    text = "some hidden words here"
    page = Page.from_html(f'<div style="display:none">{text}</div>')
    page.hidden_text = [HiddenText("div", ["display:none"], text)]
    findings = CssHiding().scan(page) + RenderDiff().scan(page)
    [merged] = merge_findings(findings)
    assert merged.detectors == ("css_hiding", "render_diff")
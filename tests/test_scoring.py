from unseen.detectors.base import Finding, Severity
from unseen.scoring import merge_findings, overall_severity


def make(detector, severity, location="comment in body", message="msg"):
    return Finding(
        detector=detector,
        severity=severity,
        message=message,
        location=location,
        snippet="snippet",
    )


def test_same_location_is_merged():
    findings = [
        make("html_comments", Severity.HIGH, message="a"),
        make("instruction_patterns", Severity.MEDIUM, message="b"),
    ]
    merged = merge_findings(findings)
    assert len(merged) == 1
    assert merged[0].severity == Severity.HIGH
    assert merged[0].detectors == ("html_comments", "instruction_patterns")
    assert merged[0].messages == ("a", "b")


def test_different_locations_stay_separate():
    findings = [
        make("html_comments", Severity.LOW, location="comment in div"),
        make("hidden_attrs", Severity.HIGH, location="alt in img"),
    ]
    merged = merge_findings(findings)
    assert len(merged) == 2
    assert merged[0].severity == Severity.HIGH  # sorted highest first


def test_overall_severity():
    assert overall_severity([]) is None
    findings = [make("a", Severity.LOW), make("b", Severity.MEDIUM)]
    assert overall_severity(findings) == Severity.MEDIUM


def test_hiding_plus_instruction_is_high():
    findings = [
        make("css_hiding", Severity.LOW, location="div"),
        make("instruction_patterns", Severity.MEDIUM, location="div"),
    ]
    merged = merge_findings(findings)
    assert len(merged) == 1
    assert merged[0].severity == Severity.HIGH


def test_instruction_alone_stays_medium():
    findings = [make("instruction_patterns", Severity.MEDIUM, location="p")]
    merged = merge_findings(findings)
    assert merged[0].severity == Severity.MEDIUM


def test_hiding_alone_keeps_its_severity():
    findings = [make("css_hiding", Severity.LOW, location="div")]
    merged = merge_findings(findings)
    assert merged[0].severity == Severity.LOW    
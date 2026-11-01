import pytest

from unseen.render import RenderError, render_hidden_text

try:
    render_hidden_text("<p>x</p>")
except RenderError as error:
    pytest.skip(f"browser not available: {error}", allow_module_level=True)


def test_visible_page_has_no_hidden_text():
    assert render_hidden_text("<p>hello world</p>") == []


def test_display_none_inline():
    [hit] = render_hidden_text('<div style="display:none">secret words</div>')
    assert hit.location == "div"
    assert hit.reasons == ["display:none"]
    assert hit.text == "secret words"


def test_rule_inside_media_query_is_applied():
    html = "<style>@media all { .x { display: none } }</style><p class='x'>secret words</p>"
    [hit] = render_hidden_text(html)
    assert hit.location == "p.x"
    assert "display:none" in hit.reasons


def test_specificity_is_respected():
    html = (
        "<style>p { display: none } p.show { display: block }</style>"
        "<p class='show'>visible</p><p>gone</p>"
    )
    [hit] = render_hidden_text(html)
    assert hit.text == "gone"


def test_hidden_parent_is_reported_once():
    [hit] = render_hidden_text('<div style="display:none"><p>secret</p><p>more</p></div>')
    assert hit.location == "div"
    assert hit.text == "secret more"


def test_zero_opacity_is_inherited():
    [hit] = render_hidden_text('<div style="opacity:0"><p>secret</p></div>')
    assert hit.location == "div"
    assert "opacity:0" in hit.reasons


def test_off_screen_position():
    [hit] = render_hidden_text('<div style="position:absolute;left:-9999px">secret</div>')
    assert hit.location == "div"
    assert "off-screen position" in hit.reasons


def test_font_size_zero():
    [hit] = render_hidden_text('<p style="font-size:0">secret</p>')
    assert "font-size:0" in hit.reasons


def test_white_text_on_white_background():
    [hit] = render_hidden_text('<p style="color:#fff">secret</p>')
    assert hit.location == "p"
    assert "text color equals background" in hit.reasons


def test_network_requests_are_blocked():
    assert render_hidden_text('<img src="http://example.com/x.png"><p>ok</p>') == []


def test_script_text_is_ignored():
    assert render_hidden_text('<p>hi</p><script>var x = "secret";</script>') == []
"""Render a page in a real browser and report text a human cannot see."""

from __future__ import annotations

from dataclasses import dataclass

TIMEOUT_MS = 10_000

# Runs inside the page. For every text node it asks the browser for the final computed
# style and records why the text would be invisible. Each problem is attributed to the
# outermost element that causes it, so labels match the css_hiding detector.
HIDDEN_TEXT_SCRIPT = r"""
() => {
  const SKIP = "script,style,noscript,template,head,title,meta,link";
  const label = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    if (el.classList.length) s += "." + Array.from(el.classList).join(".");
    return s;
  };
  const rgba = (value) => {
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const depth = (el) => {
    let d = 0;
    for (let n = el; n; n = n.parentElement) d++;
    return d;
  };
  const offscreen = (r) => r.right <= 0 || r.bottom <= 0 || r.left >= window.innerWidth + 1000;
  const clipped = (c) => {
    const k = c.clip.replace(/\s/g, "");
    const p = c.clipPath.replace(/\s/g, "");
    return k === "rect(0px,0px,0px,0px)" || p.startsWith("inset(100%") || p.startsWith("inset(50%");
  };

  const results = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const text = node.textContent.trim();
    const el = node.parentElement;
    if (!text || !el || el.closest(SKIP)) continue;

    const chain = [];
    for (let a = el; a; a = a.parentElement) chain.unshift(a);
    const outermost = (test) => chain.find(test) || el;
    const found = [];

    let opacity = 1;
    let displayNone = false;
    let opacitySource = null;
    let visibilitySource = null;
    for (const a of chain) {
      const cs = getComputedStyle(a);
      if (cs.display === "none") {
        found.push([a, "display:none"]);
        displayNone = true;
        break;
      }
      opacity *= parseFloat(cs.opacity);
      if (opacity <= 0.01 && !opacitySource) opacitySource = a;
      const hidden = cs.visibility === "hidden" || cs.visibility === "collapse";
      if (hidden && !visibilitySource) visibilitySource = a;
      if (!hidden) visibilitySource = null;
    }

    if (!displayNone) {
      if (opacitySource) found.push([opacitySource, "opacity:0"]);
      if (visibilitySource) found.push([visibilitySource, "visibility:hidden"]);

      const cs = getComputedStyle(el);
      if (parseFloat(cs.fontSize) <= 1) {
        const test = (a) => parseFloat(getComputedStyle(a).fontSize) <= 1;
        found.push([outermost(test), "font-size:0"]);
      }

      const range = document.createRange();
      range.selectNodeContents(node);
      if (offscreen(range.getBoundingClientRect())) {
        const test = (a) => offscreen(a.getBoundingClientRect());
        found.push([outermost(test), "off-screen position"]);
      }

      const clippedAncestor = chain.find((a) => clipped(getComputedStyle(a)));
      if (clippedAncestor) found.push([clippedAncestor, "clipped to nothing"]);

      const tiny = chain.find((a) => {
        const c = getComputedStyle(a);
        const small = a.offsetWidth <= 1 || a.offsetHeight <= 1;
        return c.overflow === "hidden" && c.display !== "inline" && small;
      });
      if (tiny) found.push([tiny, "zero-size container"]);

      const fg = rgba(cs.color);
      let bg = { r: 255, g: 255, b: 255, a: 1 };
      let imageBackground = false;
      for (let i = chain.length - 1; i >= 0; i--) {
        const c = getComputedStyle(chain[i]);
        if (c.backgroundImage !== "none") {
          imageBackground = true;
          break;
        }
        const b = rgba(c.backgroundColor);
        if (b && b.a > 0.99) {
          bg = b;
          break;
        }
      }
      const sameColor = (a) => getComputedStyle(a).color === cs.color;
      if (fg && fg.a <= 0.01) {
        found.push([outermost(sameColor), "transparent text"]);
      } else if (fg && !imageBackground && fg.r === bg.r && fg.g === bg.g && fg.b === bg.b) {
        found.push([outermost(sameColor), "text color equals background"]);
      }
    }

    if (!found.length) continue;
    found.sort((x, y) => depth(x[0]) - depth(y[0]));
    const source = found[0][0];
    if (!results.has(source)) results.set(source, { reasons: new Set(), texts: [] });
    const item = results.get(source);
    for (const [, reason] of found) item.reasons.add(reason);
    item.texts.push(text);
  }

  return Array.from(results, ([el, item]) => ({
    location: label(el),
    reasons: Array.from(item.reasons),
    text: item.texts.join(" "),
  }));
}
"""


class RenderError(Exception):
    """Raised when the browser is missing or the page cannot be rendered."""


@dataclass(frozen=True)
class HiddenText:
    location: str  # same "tag#id.class" label the detectors use, so findings merge
    reasons: list[str]
    text: str


def render_hidden_text(html: str, timeout_ms: int = TIMEOUT_MS) -> list[HiddenText]:
    """Render html in Chromium (network blocked) and return the text a human cannot see."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RenderError(
            "Playwright is not installed. Run: python -m pip install playwright, "
            "then: python -m playwright install chromium"
        ) from error

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                context = browser.new_context()
                context.route("**/*", lambda route: route.abort())
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                page.set_content(html, wait_until="load")
                records = page.evaluate(HIDDEN_TEXT_SCRIPT)
            finally:
                browser.close()
    except Exception as error:
        raise RenderError(f"could not render page: {error}") from error

    return [HiddenText(r["location"], r["reasons"], r["text"]) for r in records]
# unseen: progress tracker

Paste this file at the start of any new chat with Claude.

## Rules
- Go one step at a time. Wait for me to confirm before the next step.
- Give full code, not snippets.
- Don't change working code without telling me why.
- Keep tests, the SSRF guard and the benchmark. Never cut them.
- Never deploy the web version before `net_guard.py` exists.
- Update this file in the same commit as the code it describes.
- Search the repo with `git grep -n <name>` before calling code unused.

## Roadmap
| Step | Work | Status |
|---|---|---|
| 1 | README | DONE |
| 2 | Fixtures (17 poisoned, 2 clean) plus test that runs every fixture | DONE |
| 3 | report.py (rich output), used by cli.py | DONE |
| 4 | Remove leftover TextExtractor and scan_html | DONE |
| 4b | Normalize text and narrow patterns in instruction_patterns.py | DONE |
| 5 | --sanitize (sanitize.py) | DONE |
| 6 | Playwright render (render.py), detector 6 (render_diff), --render flag | DONE |
| 7 | FastAPI POST /scan | next |
| 8 | React + Tailwind side-by-side UI | todo |
| 9 | net_guard.py (SSRF), rate limits, size and time limits | todo |
| 10 | Docker and Caddy (HTTPS) | todo |
| 11 | Deploy to Oracle, open ports 80/443 in security list and server firewall | todo |
| 12 | Benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+ | todo |
| 13 | README with demo GIF, PyPI, public repo, write-up | todo |

Target: launch around Nov 10-13 (about 3 days ahead of the compressed plan).

## Current state (Nov 1, verified)
- 6 detectors registered: css_hiding, invisible_unicode, html_comments, hidden_attrs, instruction_patterns, render_diff
- patterns.py: shared normalize() and find_instruction() used by detectors 2-4
- instruction_patterns.py normalizes text first; role-spoofing and send-password patterns narrowed to avoid false positives
- fetcher.py: httpx, 10 s timeout, 2 MB cap, manual redirect loop with a validator hook for net_guard
- cli.py fetches only through fetcher.py (no urllib); local .html files also accepted
- scoring.py merges findings by location; hiding + instruction on the same location = HIGH
- report.py: rich terminal output (same text as before, colors added)
- `unseen scan <target>` with --json, --min-severity, --fail-on (default high), --sanitize FILE, --render
- Exit codes: 0 ok, 1 risk at or above --fail-on, 2 error (including missing Playwright with --render)
- Fixtures: tests/make_fixtures.py generates tests/fixtures/poisoned, clean, expected.json
- sanitize.py: removes CSS-hidden elements, aria-hidden elements with instructions, comments, script/style/noscript/head/meta, invisible Unicode; works on a fresh copy of the page
- `--sanitize FILE` writes cleaned text to FILE; the summary line goes to stderr so --json stays valid
- render.py: loads the page HTML in headless Chromium (Playwright) with ALL network requests blocked, walks every text node, and reports text a human cannot see (display:none, opacity, visibility, font-size, off-screen, clipped, zero-size container, text color = background), attributed to the outermost element using the same label as css_hiding (div#id.class) so findings merge
- Page has an optional hidden_text field (None unless --render); render_diff returns nothing when it is None
- Playwright is an optional install: `pip install unseen[render]` then `python -m playwright install chromium`
- Verified: 88 tests passing, ruff clean

## Known gaps
- css_hiding ignores external stylesheets and selector specificity (render_diff covers specificity; external stylesheets are not loaded because the browser has no network)
- Allow external stylesheets in the browser only after net_guard.py exists (step 9)
- sanitize.py uses static CSS only; it does not use the render results yet
- "zero-size container" and "off-screen position" may false-positive on accordions and carousels (tune in step 12)
- Visible-text instructions are only reported at MEDIUM by detector 5
- Phrase lists are English only
- No real-site false-positive testing yet (step 12)
- Page scripts run inside the browser (network blocked, 10 s limit); revisit limits in step 9

## Decisions
- Environment: Windows, PowerShell, VS Code, venv in `.venv`, ruff line length 100
- Layout: `src/unseen/`, detectors in `src/unseen/detectors/`, shared phrase check in `patterns.py`
- Web version: React + Tailwind frontend, FastAPI backend, Docker + Caddy on an Oracle ARM VM (A1.Flex, 1 OCPU, 6 GB)
- Playwright is allowed on the server, limited to 1 render at a time
- Limits for the web version: 10 s timeout, 2 MB page cap, per-IP rate limit
- Never put server IPs, keys or tokens in this file

## Next step
Step 7: FastAPI POST /scan. It takes a URL (or HTML), runs the same scan as the CLI, and returns the
JSON the CLI prints. It must reuse scan_page, not copy the logic. No public deploy until net_guard.py (step 9).
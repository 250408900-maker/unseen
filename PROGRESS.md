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
| 7 | FastAPI POST /scan (api.py) | DONE |
| 8 | React + Tailwind side-by-side UI | next |
| 9 | net_guard.py (SSRF), rate limits, size and time limits | todo |
| 10 | Docker and Caddy (HTTPS) | todo |
| 11 | Deploy to Oracle, open ports 80/443 in security list and server firewall | todo |
| 12 | Benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+ | todo |
| 13 | README with demo GIF, PyPI, public repo, write-up | todo |

Target: launch around Nov 10-13 (about 3 days ahead of the compressed plan).

## Current state (Nov 2, verified)
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
- render.py: loads the page HTML in headless Chromium (Playwright) with ALL network requests blocked, walks every text node, and reports text a human cannot see, attributed to the outermost element using the same label as css_hiding (div#id.class) so findings merge
- Page has an optional hidden_text field (None unless --render); render_diff returns nothing when it is None
- Playwright is an optional install: `pip install unseen[render]` then `python -m playwright install chromium`
- api.py (FastAPI): GET /health and POST /scan. Body: exactly one of `url` (http/https only) or `html` (max 2,000,000 chars), plus `render`, `sanitize`, `min_severity`. Returns the same JSON as `--json` (target, overall, findings) plus a `sanitized` block when requested
- API never reads local files (it does not use load_page); url goes through fetcher.fetch
- API errors: 422 bad input, 502 fetch failed, 503 render unavailable, 429 another render is running (one render at a time via RENDER_LOCK)
- Run locally: `python -m uvicorn unseen.api:app` (127.0.0.1:8000, docs at /docs). Install: `python -m pip install -e ".[api]"`
- Verified: 103 tests passing, ruff clean, API tried by hand in the /docs page

## Known gaps
- css_hiding ignores external stylesheets and selector specificity (render_diff covers specificity; external stylesheets are not loaded because the browser has no network)
- Allow external stylesheets in the browser only after net_guard.py exists (step 9)
- sanitize.py uses static CSS only; it does not use the render results yet
- "zero-size container" and "off-screen position" may false-positive on accordions and carousels (tune in step 12)
- Visible-text instructions are only reported at MEDIUM by detector 5
- Phrase lists are English only
- No real-site false-positive testing yet (step 12)
- Page scripts run inside the browser (network blocked, 10 s limit); revisit limits in step 9
- api.py imports scan_page and overall from cli.py; move them to a shared module later
- API has no CORS settings yet (needed for the React dev server in step 8), no rate limit and no SSRF guard (step 9): localhost only
- pytest shows a Starlette warning about httpx vs httpx2 in the test client (harmless)

## Decisions
- Environment: Windows, PowerShell, VS Code, venv in `.venv`, ruff line length 100
- Layout: `src/unseen/`, detectors in `src/unseen/detectors/`, shared phrase check in `patterns.py`
- Web version: React + Tailwind frontend, FastAPI backend, Docker + Caddy on an Oracle ARM VM (A1.Flex, 1 OCPU, 6 GB)
- Playwright is allowed on the server, limited to 1 render at a time
- Limits for the web version: 10 s timeout, 2 MB page cap, per-IP rate limit
- Never put server IPs, keys or tokens in this file

## Next step
Step 8: React + Tailwind side-by-side UI. Left: the raw page text with the hidden parts highlighted.
Right: the cleaned text from `sanitize: true`. It calls POST /scan. Needs CORS for the dev server
(localhost only). Check Node.js is installed first (`node --version`).
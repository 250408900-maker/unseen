# unseen: progress tracker

Paste this file at the start of any new chat with Claude.

## Rules
- Go one step at a time. Wait for me to confirm before the next step.
- Give full code, not snippets.
- Don't change working code without telling me why.
- Keep tests, the SSRF guard and the benchmark. Never cut them.
- Never deploy the web version before `net_guard.py` exists. (It exists now; see step 9.)
- Update this file in the same commit as the code it describes.
- Search the repo with `git grep -n <name>` before calling code unused.
- Copy only the text inside code boxes; never paste terminal prompt lines (a `>` creates stray files).
- To show Claude a file, open it in VS Code, Ctrl+A, Ctrl+C, paste into the chat. Never type a file path into the terminal.

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
| 8 | React + Tailwind UI (web/) | DONE |
| 9 | net_guard.py (SSRF), rate limits, size and time limits | DONE |
| 10 | Docker and Caddy (HTTPS) | next |
| 11 | Deploy to Oracle, open ports 80/443 in security list and server firewall | todo |
| 12 | Benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+ | todo |
| 13 | README with demo GIF, PyPI, public repo, write-up | todo |

Target: launch around Nov 10-13 (about 3 days ahead of the compressed plan).

## Current state (Nov 3, verified)
- 6 detectors registered: css_hiding, invisible_unicode, html_comments, hidden_attrs, instruction_patterns, render_diff
- patterns.py: shared normalize() and find_instruction() used by detectors 2-4
- instruction_patterns.py normalizes text first; role-spoofing and send-password patterns narrowed to avoid false positives
- scoring.py merges findings by location; hiding + instruction on the same location = HIGH
- report.py: rich terminal output
- `unseen scan <target>` with --json, --min-severity, --fail-on (default high), --sanitize FILE, --render
- Exit codes: 0 ok, 1 risk at or above --fail-on, 2 error (including missing Playwright with --render)
- cli.py fetches only through fetcher.py (no urllib); local .html files also accepted
- Fixtures: tests/make_fixtures.py generates tests/fixtures/poisoned, clean, expected.json
- sanitize.py: removes CSS-hidden elements, aria-hidden elements with instructions, comments, script/style/noscript/head/meta, invisible Unicode; works on a fresh copy of the page
- render.py: loads the page HTML in headless Chromium (Playwright) with ALL network requests blocked, reports text a human cannot see, attributed to the outermost element using the same label as css_hiding so findings merge
- Page has an optional hidden_text field (None unless --render); render_diff returns nothing when it is None
- Playwright is an optional install: `pip install unseen[render]` then `python -m playwright install chromium`
- net_guard.py (SSRF guard): http/https only, ports 80 and 443 only, no embedded credentials, every resolved address must be globally routable (private, loopback, link-local, metadata, CGNAT, multicast refused); IPv4-mapped, 6to4 and NAT64 IPv6 forms are unwrapped and checked as IPv4. make_validator() returns the approved IPs
- fetcher.py: httpx, 10 s per-request timeout, 15 s total deadline (checked on every hop and every body chunk), 2 MB cap, max 5 redirects handled manually, trust_env=False (ignores proxy env vars). The validator runs on the first URL and on every redirect, and the connection is pinned to an approved IP (Host header kept, SNI and certificate check use the original name), so DNS rebinding is closed
- ratelimit.py: in-memory sliding window per visitor, thread-safe, max 10,000 keys with pruning, blocked hits not recorded
- api.py (FastAPI): GET /health and POST /scan. Body: exactly one of `url` (http/https only) or `html` (max 2,000,000 chars), plus `render`, `sanitize`, `min_severity`. Returns target, overall, findings, and a `sanitized` block when requested
- API limits: 10 scans per visitor per minute, 3 renders per visitor per minute, one render at a time (RENDER_LOCK), body over 3,000,000 bytes (Content-Length) gets 413. Visitor = client IP, IPv6 grouped by /64. X-Forwarded-For is used only when env UNSEEN_TRUST_PROXY=1 (last entry)
- API never reads local files (it does not use load_page); url goes through fetcher.fetch with the SSRF validator
- API errors: 413 body too large, 422 bad input, 429 rate limit or another render running, 502 fetch failed, 503 render unavailable
- web/: Vite 8 + React + Tailwind 4 (JavaScript). One page in web/src/App.jsx: "Paste HTML" and "Scan a URL" tabs, "Also check in a real browser" checkbox, "Load an example" button, findings cards on the left, cleaned text on the right. All scanned text is rendered as plain text (never as HTML)
- Dev setup: two terminals. (1) `python -m uvicorn unseen.api:app` from the project root, (2) `cd web` then `npm run dev` (http://localhost:5173). Vite proxies /api/* to http://127.0.0.1:8000/* (prefix removed), so no CORS settings are needed
- Production build works (`npm run build` in web/ makes web/dist; node_modules and dist are git-ignored by web/.gitignore)
- Tests for step 9: test_net_guard.py, test_fetch_redirects.py (redirect blocking, IP pinning, rebinding, total deadline, trust_env), test_ratelimit.py, test_api.py
- Verified: 199 Python tests passing, ruff clean

## Known gaps
- css_hiding ignores external stylesheets and selector specificity (render_diff covers specificity; external stylesheets are not loaded because the browser has no network). net_guard now exists, so loading external stylesheets through the guard can be considered in step 12
- sanitize.py uses static CSS only; it does not use the render results yet
- "zero-size container" and "off-screen position" may false-positive on accordions and carousels (tune in step 12)
- Visible-text instructions are only reported at MEDIUM by detector 5
- Phrase lists are English only
- No real-site false-positive testing yet (step 12)
- Page scripts run inside the browser (network blocked, 10 s limit); render.py was not re-reviewed in step 9
- api.py imports scan_page and overall from cli.py; move them to a shared module later
- Rate limiter and RENDER_LOCK live in process memory: the API must run with exactly ONE uvicorn worker
- The 413 body check reads Content-Length only; chunked uploads skip it (Caddy must cap the body, step 10)
- UI shows findings and cleaned text side by side, but does not highlight hidden parts inside the raw page text
- Web UI has no automated tests; `npm audit` reports issues in dev dependencies that have not been reviewed
- pytest shows a Starlette warning about httpx vs httpx2 in the test client (harmless; leave until after deploy)

## Decisions
- Environment: Windows, PowerShell, VS Code, venv in `.venv`, ruff line length 100, Node 24
- Layout: `src/unseen/`, detectors in `src/unseen/detectors/`, shared phrase check in `patterns.py`, frontend in `web/`
- Web version: React + Tailwind frontend, FastAPI backend, Docker + Caddy on an Oracle ARM VM (A1.Flex, 1 OCPU, 6 GB)
- Playwright is allowed on the server, limited to 1 render at a time
- Limits for the web version: 10 s per-request timeout, 15 s total, 2 MB page cap, per-IP rate limit
- Never put server IPs, keys or tokens in this file

## Next step
Step 10: Docker and Caddy (HTTPS). Requirements from step 9:
- Run uvicorn with exactly one worker.
- Set UNSEEN_TRUST_PROXY=1 in the API container; never publish the API port. Caddy is the only way in.
- Caddy: proxy /api/* to the API and strip the /api prefix, serve web/dist, set `request_body { max_size 3MB }`.
- Playwright and Chromium must work inside the image (ARM64).
- After the containers run locally, confirm that POST /scan with url http://169.254.169.254/ and http://127.0.0.1/ is refused before step 11.
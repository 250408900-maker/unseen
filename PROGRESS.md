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
| 5 | --sanitize (sanitize.py) | next |
| 6 | Playwright render and detector 6 (visible vs. extracted diff) | todo |
| 7 | FastAPI POST /scan | todo |
| 8 | React + Tailwind side-by-side UI | todo |
| 9 | net_guard.py (SSRF), rate limits, size and time limits | todo |
| 10 | Docker and Caddy (HTTPS) | todo |
| 11 | Deploy to Oracle, open ports 80/443 in security list and server firewall | todo |
| 12 | Benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+ | todo |
| 13 | README with demo GIF, PyPI, public repo, write-up | todo |

Target: launch around Nov 10-13 (about 3 days ahead of the compressed plan).

## Current state (Nov 1, verified)
- 5 detectors registered: css_hiding, invisible_unicode, html_comments, hidden_attrs, instruction_patterns
- patterns.py: shared normalize() and find_instruction() used by detectors 2-4
- instruction_patterns.py normalizes text first; role-spoofing and send-password patterns narrowed to avoid false positives
- fetcher.py: httpx, 10 s timeout, 2 MB cap, manual redirect loop with a validator hook for net_guard
- cli.py fetches only through fetcher.py (no urllib); local .html files also accepted
- scoring.py merges findings by location; hiding + instruction on the same location = HIGH
- report.py: rich terminal output (same text as before, colors added)
- `unseen scan <target>` with --json, --min-severity, --fail-on (default high)
- Exit codes: 0 ok, 1 risk at or above --fail-on, 2 error
- Fixtures: tests/make_fixtures.py generates tests/fixtures/poisoned, clean, expected.json
- Verified: 55 tests passing, ruff clean, CI green on 3.10 and 3.12 up to the CLI fix

## Known gaps
- css_hiding ignores external stylesheets, media queries and selector specificity
- Visible-text instructions are only reported at MEDIUM by detector 5
- Phrase lists are English only
- No real-site false-positive testing yet (step 12)

## Decisions
- Environment: Windows, PowerShell, VS Code, venv in `.venv`, ruff line length 100
- Layout: `src/unseen/`, detectors in `src/unseen/detectors/`, shared phrase check in `patterns.py`
- Web version: React + Tailwind frontend, FastAPI backend, Docker + Caddy on an Oracle ARM VM (A1.Flex, 1 OCPU, 6 GB)
- Playwright is allowed on the server, limited to 1 render at a time
- Limits for the web version: 10 s timeout, 2 MB page cap, per-IP rate limit
- Never put server IPs, keys or tokens in this file

## Next step
Step 5: sanitize.py and `--sanitize`. Output is a cleaned text version of the page with every flagged
element and invisible character removed, safe to give a model.
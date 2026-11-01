# unseen: progress tracker

Paste this file at the start of any new chat with Claude.

## Rules
- Go one step at a time. Wait for me to confirm before the next step.
- Give full code, not snippets.
- Don't change working code without telling me why.
- Keep tests, the SSRF guard and the benchmark. Never cut them.
- Never deploy the web version before `net_guard.py` exists.
- Update this file in the same commit as the code it describes.

## Roadmap (compressed plan, launch around Nov 13-15)
| Day | Dates | Work | Status |
|---|---|---|---|
| 1 | Nov 1-2 | Detectors 2-5, README | detectors DONE, README todo |
| 2 | Nov 3 | Fixtures and pytest for all detectors | tests DONE, fixtures todo |
| 3 | Nov 4 | Scanner, scoring, report, CLI: `unseen scan <url>` | mostly DONE (no report.py) |
| 4 | Nov 5 | --sanitize, Playwright render, detector 6 | todo |
| 5-6 | Nov 6-7 | FastAPI endpoint, React side-by-side UI | todo |
| 7 | Nov 8 | net_guard.py (SSRF), rate limits, Docker | todo |
| 8 | Nov 9 | Deploy to Oracle, HTTPS, open ports | todo |
| 9-10 | Nov 10-11 | Benchmark, false-positive tuning, coverage | todo |
| 11 | Nov 12 | README with GIF, PyPI, public repo, write-up | todo |
| 12-13 | Nov 13-14 | Buffer | |

## Current state (Nov 1, verified)
- 5 detectors registered: css_hiding, invisible_unicode, html_comments, hidden_attrs, instruction_patterns
- fetcher.py exists (httpx, 10 s timeout, 2 MB cap, manual redirect loop with a validator hook for net_guard)
- scoring.py merges findings by location; hiding + instruction on the same location = HIGH
- cli.py: `unseen scan <target>`, `--json`, `--min-severity`, `--fail-on` (default high)
- Exit codes: 0 ok, 1 risk at or above --fail-on, 2 error
- Verified: 23 tests passing, ruff clean
- CI: GitHub Actions (Python 3.10 and 3.12), green

## Decisions
- Environment: Windows, PowerShell, VS Code, venv in `.venv`, ruff line length 100
- Layout: `src/unseen/`, detectors in `src/unseen/detectors/`, shared phrase check in `patterns.py`
- Web version: React + Tailwind frontend, FastAPI backend, Docker + Caddy on an Oracle ARM VM (A1.Flex, 1 OCPU, 6 GB)
- Playwright is allowed on the server, limited to 1 render at a time
- Limits for the web version: 10 s timeout, 2 MB page cap, per-IP rate limit
- Never put server IPs, keys or tokens in this file

## Next steps, in order
1. Short README (only what exists today)
2. Fixtures plus a test that runs every fixture
3. report.py, moved out of cli.py
4. Delete leftover TextExtractor and scan_html in instruction_patterns.py
5. --sanitize, then Playwright render and detector 6
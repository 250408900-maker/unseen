# unseen: progress tracker

Paste this file at the start of any new chat with Claude.

## Rules
- Go one step at a time. Wait for me to confirm before the next step.
- Give full code, not snippets.
- Don't change working code without telling me why.
- Keep tests, the SSRF guard and the benchmark. Never cut them.
- Never deploy the web version without net_guard.py (it exists and is verified inside the containers).
- Update this file in the same commit as the code it describes.
- Search the repo with `git grep -n <name>` before calling code unused.
- Copy only the text inside code boxes; never paste terminal prompt lines (a `>` creates stray files).
- To show Claude a file, open it in VS Code, Ctrl+A, Ctrl+C, paste into the chat. Never type a file path into the terminal.
- When creating a file in VS Code, click the project root folder (`unseen`) first so the file is not created inside `web` or `src`. Check with `dir <name>`.
- In PowerShell, send JSON to curl through a file (`--data-binary "@file.json"`), never inline.

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
| 10 | Docker and Caddy (HTTPS) | DONE (tested locally) |
| 11 | Deploy to Oracle, open ports 80/443 in security list and server firewall | next |
| 12 | Benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+ | todo |
| 13 | README with demo GIF, PyPI, public repo, write-up | todo |

Target: launch around Nov 10-13.

## Current state (Nov 4, verified)
- Detectors, CLI, sanitize, render, API, web UI, SSRF guard, rate limits: see steps 1-9 (all DONE). 199 Python tests passing, ruff clean
- 6 detectors: css_hiding, invisible_unicode, html_comments, hidden_attrs, instruction_patterns, render_diff
- net_guard.py: http/https only, ports 80/443 only, no embedded credentials, every resolved IP
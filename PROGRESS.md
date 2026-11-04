# unseen: progress tracker

Paste this file at the start of any new chat with Claude.

## Rules
- Go one step at a time. Wait for me to confirm before the next step.
- Give full code, not snippets.
- Don't change working code without telling me why.
- Keep tests, the SSRF guard and the benchmark. Never cut them.
- Update this file in the same commit as the code it describes.
- Search the repo with `git grep -n <name>` before calling code unused.
- Copy only the text inside code boxes; never paste terminal prompt lines.
- To show Claude a file, open it in VS Code, Ctrl+A, Ctrl+C, paste into the chat. Never type a file path into the terminal.
- Create files with the project root folder selected in VS Code. Check with `dir <name>`.
- In PowerShell, send JSON to curl through a file (`--data-binary "@file.json"`).
- Never put server IPs, keys or tokens in this file.

## Roadmap
| Step | Work | Status |
|---|---|---|
| 1-9 | README, fixtures, report, sanitize, render, API, web UI, SSRF guard, rate limits | DONE |
| 10 | Docker and Caddy | DONE |
| 11 | Deploy to Oracle (existing VPN server) | DONE |
| 12 | Benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+ | next |
| 13 | README with demo GIF, PyPI, public repo, write-up | todo |

Target: launch around Nov 10-13.

## Current state (Nov 4, verified)
- 199 Python tests passing, ruff clean. Code, Dockerfile, Caddyfile, compose: see repo
- Live at https://unseen-scan.duckdns.org:9443 (DuckDNS name points at the Oracle server). Always use the :9443 URL
- Runs on the EXISTING Oracle server (Oracle Linux 9, aarch64, user opc, 1 OCPU, 6 GB), which also hosts the VPN. Project folder on the server: /home/opc/unseen
- Port 443 on that server belongs to OpenVPN, so compose maps host 9443 to Caddy's 443 ("9443:443") and host 80 to 80 (needed for the certificate). Firewalld has 80/tcp and 9443/tcp open; the Oracle security list allows them
- On the server, SITE_ADDRESS=unseen-scan.duckdns.org is set directly inside docker-compose.yml (no .env). In the repo the default is :80 for local use
- Verified live: page loads; example scan works with "real browser" ticked (Chromium works on ARM); http://127.0.0.1/ and http://169.254.169.254/ are refused; port 8000 not reachable from the internet; about 4.2 GB RAM available at idle
- ARM64 image also built on the PC with `docker buildx build --platform linux/arm64`
- SSH: key oracle_vpn.key (a locked-down copy in C:\Users\user\.ssh\) logs in as opc. A second key pair, oracle_unseen, was made for a new server that Oracle had no capacity for; not used

## Known gaps
- The server's files are an older copy (its README.md is empty); sync it with the repo before the next redeploy. Rebuild web/dist before copying
- Caddy's http-to-https redirect goes to port 443 (OpenVPN), so only the direct :9443 link works
- Memory at peak render was not measured; check `free -h` during a render
- Rate limiter and RENDER_LOCK are in process memory: exactly ONE uvicorn worker
- css_hiding ignores external stylesheets; "zero-size container" and "off-screen position" may false-positive; phrase lists English only; no real-site false-positive testing yet
- api.py imports scan_page and overall from cli.py; move to a shared module later
- Web UI has no automated tests; npm audit issues in dev dependencies not reviewed
- Starlette httpx warning in tests is harmless

## Decisions
- Environment: Windows, PowerShell, VS Code, venv in .venv, ruff line length 100, Node 24
- Web version: React + Tailwind, FastAPI, Docker + Caddy; Playwright limited to 1 render at a time
- Limits: 10 s per request, 15 s total, 2 MB page cap, 10 scans/min and 3 renders/min per visitor
- If a clean Oracle server with free 80/443 becomes available, move there and drop the :9443 workaround

## Next step
Step 12: benchmark (15+ fixtures), false-positive tuning on real sites, coverage 80%+.
# healthping

A lightweight, async-first HTTP health monitor with a live web dashboard and webhook alerts. Define endpoints in a YAML file, run one command, get a real-time status dashboard plus Slack/Discord notifications when anything changes.

---

## Features

- **Async concurrent checks** — all endpoints polled in parallel using a shared connection pool
- **Live web dashboard** — Next.js 16 + shadcn/ui, auto-refreshes every 10 seconds, clean on mobile and desktop
- **Structured JSON logs** — every check emitted as parseable JSON, ready for Loki / Datadog / any aggregator
- **Webhook alerts on state transitions** — only alerts on up→down and down→up, no noise
- **Slack or Discord** — same config, different platforms
- **Per-endpoint configuration** — interval, timeout, expected status, and method all tuneable
- **Fault tolerant** — no single failure (timeout, DNS, broken webhook) can crash the monitor
- **Fully dockerized** — backend and frontend each in their own container, one compose command to run

---

## Architecture

```
┌──────────────┐         ┌──────────────────────┐
│  Next.js UI  │◄────────│  FastAPI HTTP API    │
│  (port 3000) │  REST   │  /api/status         │
└──────────────┘         │  /api/health         │
                         └──────────┬───────────┘
                                    │ shared state
                         ┌──────────▼───────────┐
                         │  Monitor loops       │
                         │  (one task per       │
                         │   endpoint, async)   │
                         └──────────┬───────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
                 endpoint 1    endpoint 2    endpoint N
                                    │
                                    │ on state change
                                    ▼
                           ┌────────────────┐
                           │ Slack/Discord  │
                           │    webhook     │
                           └────────────────┘
```

---

## Quick start

### Full stack with Docker Compose

```bash
git clone git@github.com:elias-abr/healthping.git
cd healthping
docker compose up --build
```

Visit `http://localhost:3000` for the dashboard, `http://localhost:8000/api/status` for the raw API.

### Backend only (CLI mode)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
healthping monitor --config config.example.yaml
```

### Backend with API (no frontend)

```bash
healthping serve --config config.example.yaml
```

---

## Configuration

Configuration lives in a YAML file. Minimal config:

```yaml
endpoints:
  - name: my-api
    url: https://api.example.com/health
```

Full config with all options:

```yaml
endpoints:
  - name: api
    url: https://api.example.com/health
    method: GET # GET | POST | HEAD, default GET
    timeout_seconds: 5 # default 5
    expected_status: 200 # default 200
    interval_seconds: 30 # minimum 5, default 30

  - name: auth-service
    url: https://auth.example.com
    method: HEAD
    interval_seconds: 60

alerts:
  platform: discord # or "slack"
  webhook_url: https://discord.com/api/webhooks/XXX/YYY
```

---

## Output

Every check emits a single JSON log line to stdout:

```json
{
  "endpoint_name": "api",
  "url": "https://api.example.com/health",
  "status": "up",
  "response_time_ms": 142.33,
  "http_status": 200,
  "error": null,
  "timestamp": "2026-04-20T13:33:21.365Z",
  "event": "check_result",
  "level": "info"
}
```

On a state transition, a webhook alert is also posted:

> 🔴 **api** UP → DOWN
> URL: `https://api.example.com/health`
> Error: `Expected HTTP 200, got 503`
> Response time: `89.12ms`

---

## HTTP API

Available when running `healthping serve` or via Docker Compose.

### `GET /api/health`

Liveness check for the API itself.

```json
{ "status": "ok" }
```

### `GET /api/status`

Latest known status of every configured endpoint.

```json
{
  "started_at": "2026-04-20T10:00:00Z",
  "now": "2026-04-20T10:05:30Z",
  "endpoints": [
    {
      "endpoint_name": "api",
      "url": "https://api.example.com/health",
      "status": "up",
      "response_time_ms": 142.33,
      "http_status": 200,
      "error": null,
      "timestamp": "2026-04-20T10:05:25Z"
    }
  ]
}
```

Interactive OpenAPI docs available at `/docs` when running the API.

---

## Project structure

```
healthping/
├── backend/              # Python 3.12 FastAPI monitor + API
│   ├── src/healthping/
│   │   ├── api.py         # FastAPI app (read-only)
│   │   ├── state.py       # Shared in-memory state
│   │   ├── monitor.py     # Async check function
│   │   ├── cli.py         # Click CLI (monitor / serve)
│   │   ├── alerts.py      # Slack + Discord webhooks
│   │   ├── config.py      # YAML config loader
│   │   └── models.py      # Pydantic models
│   ├── tests/
│   └── Dockerfile
├── frontend/             # Next.js 16 + React 19 + Tailwind + shadcn/ui
│   ├── src/
│   │   ├── app/page.tsx           # Dashboard
│   │   ├── components/
│   │   │   └── EndpointCard.tsx
│   │   ├── lib/api.ts             # API client
│   │   └── types/status.ts
│   └── Dockerfile
└── docker-compose.yml
```

---

## Development

### Backend

```bash
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v                  # 15 tests
ruff check .
ruff format .
mypy src
```

Tests use `httpx.MockTransport` and FastAPI's `TestClient` — no real network traffic, no flakiness.

### Frontend

```bash
cd frontend
npm install
npm run dev                # http://localhost:3000
npm run lint
npm run build
```

---

## Roadmap

- [ ] v2 — Auth, endpoint management via UI, persistence
- [ ] v2 — WebSocket real-time updates (replace 10s polling)
- [ ] v2 — Historical charts (response time over time, uptime percentage)
- [ ] v2 — Alert debouncing (require N consecutive failures before notifying)

---

## License

MIT — see [LICENSE](LICENSE).

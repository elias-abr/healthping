# healthping

A lightweight, async-first HTTP health monitor with webhook alerts. Define endpoints in a YAML file, run one command, get structured JSON logs and Slack/Discord alerts when something changes state.

---

## Features

- **Async concurrent checks** — all endpoints polled in parallel using a single shared connection pool
- **Structured JSON logs** — every check emitted as a parseable log line ready for Loki, Datadog, or any aggregator
- **Webhook alerts on state transitions** — only alerts on `up → down` and `down → up`, no noise
- **Per-endpoint configuration** — interval, timeout, expected status, and method all tuneable individually
- **Fault tolerant** — no single failure (timeout, DNS, broken webhook) can crash the monitor
- **Small footprint** — ~80MB Docker image, non-root container, ~300 lines of typed Python

---

## Quick start

### With Docker (recommended)

```bash
git clone git@github.com:elias-abr/healthping.git
cd healthping
docker compose up
```

### Local Python

```bash
git clone git@github.com:elias-abr/healthping.git
cd healthping
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
healthping --config config.example.yaml
```

---

## Configuration

Configuration lives in a YAML file. Minimum viable config:

```yaml
endpoints:
  - name: my-api
    url: https://api.example.com/health
```

Full example with all options:

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
  webhook_url: https://hooks.slack.com/services/XXX/YYY/ZZZ
```

The `webhook_url` is compatible with both Slack and Discord incoming webhooks. Omit it to disable alerting.

---

## Output

Every check produces one JSON log line on stdout:

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

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint + format
ruff check .
ruff format .

# Type check
mypy src
```

Tests use `httpx.MockTransport` — no real network traffic, no flakiness.

---

## Architecture

- **`models.py`** — Pydantic domain types. All validation happens here.
- **`config.py`** — YAML loading with explicit error types.
- **`monitor.py`** — Stateless async check function. Never raises; failures become `DOWN` results.
- **`alerts.py`** — Webhook dispatcher. Alert failures are logged, never propagated.
- **`cli.py`** — Click-based CLI. Wires everything together, handles signals for clean shutdown.

All timestamps are UTC. The check loop uses a cooperative `asyncio.Event` for cancellation, so `SIGINT` / `SIGTERM` shut down cleanly even mid-sleep.

---

## License

MIT — see [LICENSE](LICENSE).

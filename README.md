# VoiceFlip Pipeline

Async processing pipeline built with Python and FastAPI.

## Run

```bash
docker compose up --build
```

API: `http://localhost:8000`
Docs: `http://localhost:8000/docs`

## Tests

```bash
docker compose run --rm api pytest tests/ -v
```

---

## API

### POST /requests — create a request

```bash
curl -X POST http://localhost:8000/requests \
  -H "Content-Type: application/json" \
  -d '{"input": "audio-123", "scenario": "ok", "optional_scenario": "ok"}'
```

Available scenarios: `ok`, `timeout`, `transient_fail_then_ok`, `hard_fail`

### GET /requests/{id} — check status

```bash
curl http://localhost:8000/requests/{id}
```

Status goes: `pending` → `running` → `completed` or `failed`

### GET /health — metrics

```bash
curl http://localhost:8000/health
```

---

## Project structure

```
app/
  api/            # HTTP endpoints
  core/           # config, schemas, store
  services/       # orchestrator, retry engine, handlers
  observability/  # metrics
tests/
```

## How it works

Both handlers (`primary` and `optional`) run in parallel.

- If `primary` fails → request fails
- If `optional` fails → request completes with `degraded: true`

Failed handlers are retried with exponential backoff and jitter. Only connection and timeout errors are retried.

---

## Video walkthrough

<!-- Add Loom link here -->

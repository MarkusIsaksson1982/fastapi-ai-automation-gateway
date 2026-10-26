# fastapi-ai-automation-gateway

Small FastAPI gateway for securely sending automation jobs to a local Ollama-compatible model.

## Setup

```bash
python -m venv .venv && .venv/bin/pip install -e .
export API_KEYS=$(printf 'change-me' | sha256sum | cut -d' ' -f1)
.venv/bin/uvicorn app.main:app --reload
```

SQLite is the default (`./app.db`). Set `DATABASE_URL` to a PostgreSQL URL for production, and set `OLLAMA_URL`, `MODEL_NAME`, `MAX_INPUT_CHARS`, and `MODEL_TIMEOUT_SECONDS` as needed. Run tests with `.venv/bin/python -m pytest`.

## Architecture and security

Routes authenticate with `X-API-Key`; only SHA-256 hashes in `API_KEYS` are stored/configured and comparisons are constant-time. Job text is redacted for email addresses, Swedish personnummer, and common Swedish phone numbers before reaching the model. Every model attempt gets an append-only audit row containing only a prompt hash, timing, status, and job ID. Model timeouts and failures mark jobs failed. The model client is a FastAPI dependency so tests or deployments can substitute an internal client.

## Examples

```bash
KEY=change-me
curl -H "X-API-Key: $KEY" http://localhost:8000/healthz
curl -X POST -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"type":"summarize","input_text":"Summarize this text"}' \
  http://localhost:8000/jobs
curl -X POST -H "X-API-Key: $KEY" http://localhost:8000/jobs/1/run
curl -H "X-API-Key: $KEY" http://localhost:8000/audit
```

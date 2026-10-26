import hashlib
import os
from pathlib import Path
import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import MAX_INPUT_CHARS
from app.database import Base, get_db
from app.main import app, client_dependency


class FakeModelClient:
    def __init__(self, failure=False): self.failure = failure; self.prompts = []
    async def generate(self, prompt):
        self.prompts.append(prompt)
        if self.failure: raise RuntimeError("offline")
        return "fake answer"


@pytest.fixture()
def anyio_backend(): return "asyncio"


@pytest.fixture()
async def client(tmp_path: Path, monkeypatch):
    key = "test-secret"
    monkeypatch.setenv("API_KEYS", hashlib.sha256(key.encode()).hexdigest())
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    fake = FakeModelClient()
    app.dependency_overrides[client_dependency] = lambda: fake
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client, key, fake
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def auth(key): return {"X-API-Key": key}


@pytest.mark.anyio
async def test_auth_and_health(client):
    c, key, _ = client
    assert (await c.get("/healthz")).json() == {"status": "ok"}
    assert (await c.get("/jobs")).status_code == 401
    assert (await c.get("/jobs", headers=auth(key))).status_code == 200


@pytest.mark.anyio
async def test_lifecycle_redaction_and_audit(client):
    c, key, fake = client
    created = await c.post("/jobs", headers=auth(key), json={"type": "summarize", "input_text": "Mail a@b.se, person 19900101-1234, ring 070-123 45 67"})
    assert created.status_code == 201
    job_id = created.json()["id"]
    result = await c.post(f"/jobs/{job_id}/run", headers=auth(key))
    assert result.json()["status"] == "completed"
    assert "a@b.se" not in fake.prompts[0]
    assert "19900101-1234" not in fake.prompts[0]
    audit = (await c.get("/audit", headers=auth(key))).json()
    assert len(audit) == 1 and audit[0]["job_id"] == job_id and audit[0]["status"] == "success"
    assert (await c.get("/jobs", headers=auth(key))).json()[0]["id"] == job_id


@pytest.mark.anyio
async def test_validation_and_model_failure(client):
    c, key, _ = client
    bad = await c.post("/jobs", headers=auth(key), json={"type": "unknown", "input_text": "x"})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"
    created = (await c.post("/jobs", headers=auth(key), json={"type": "classify", "input_text": "hello"})).json()
    failing = FakeModelClient(failure=True)
    app.dependency_overrides[client_dependency] = lambda: failing
    response = await c.post(f"/jobs/{created['id']}/run", headers=auth(key))
    assert response.json()["status"] == "failed"
    assert (await c.get("/audit", headers=auth(key))).json()[0]["status"] == "failure"


@pytest.mark.anyio
async def test_missing_and_wrong_api_key_return_401(client):
    c, _, _ = client
    missing = await c.get("/jobs")
    wrong = await c.get("/jobs", headers=auth("not-the-key"))
    for response in (missing, wrong):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
    assert (await c.post("/jobs", json={"type": "summarize", "input_text": "x"})).status_code == 401


@pytest.mark.anyio
async def test_oversized_input_is_rejected(client):
    c, key, _ = client
    response = await c.post(
        "/jobs",
        headers=auth(key),
        json={"type": "summarize", "input_text": "x" * (MAX_INPUT_CHARS + 1)},
    )
    assert response.status_code in (422, 413)
    if response.status_code == 422:
        assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.anyio
async def test_unknown_job_returns_404_json_error(client):
    c, key, _ = client
    response = await c.get("/jobs/999999", headers=auth(key))
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Job not found"}}


@pytest.mark.anyio
async def test_audit_entries_never_contain_raw_pii(client):
    c, key, _ = client
    pii = ["sensitive@example.se", "19900101-1234", "+46 70 123 45 67"]
    created = await c.post(
        "/jobs",
        headers=auth(key),
        json={"type": "summarize", "input_text": f"Mail {pii[0]}, person {pii[1]}, ring {pii[2]}"},
    )
    job_id = created.json()["id"]
    await c.post(f"/jobs/{job_id}/run", headers=auth(key))

    audit = (await c.get("/audit", headers=auth(key))).json()
    assert len(audit) == 1
    assert set(audit[0]) == {"id", "job_id", "prompt_hash", "latency_ms", "status", "created_at"}
    serialized = str(audit)
    for value in pii:
        assert value not in serialized
    assert len(audit[0]["prompt_hash"]) == 64

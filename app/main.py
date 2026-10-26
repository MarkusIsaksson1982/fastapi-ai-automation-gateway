import hashlib
import time
from collections.abc import Generator
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db, init_db
from .model_client import ModelClient
from .models import AuditLog, Job
from .redaction import redact
from .schemas import AuditRead, JobCreate, JobRead
from .security import require_api_key

app = FastAPI(title="fastapi-ai-automation-gateway", version="1.0.0")
init_db()


def client_dependency() -> ModelClient:
    return ModelClient()


def as_job(job: Job) -> dict:
    return {"id": job.id, "type": job.job_type, "input_text": job.input_text, "status": job.status, "result": job.result, "error": job.error, "created_at": job.created_at, "updated_at": job.updated_at}


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Invalid request", "details": exc.errors()}})


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", response_model=JobRead, status_code=201, dependencies=[Depends(require_api_key)])
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> dict:
    job = Job(job_type=payload.type, input_text=payload.input_text)
    db.add(job); db.commit(); db.refresh(job)
    return as_job(job)


@app.get("/jobs", response_model=list[JobRead], dependencies=[Depends(require_api_key)])
def list_jobs(db: Session = Depends(get_db)) -> list[dict]:
    return [as_job(j) for j in db.scalars(select(Job).order_by(Job.id)).all()]


@app.get("/jobs/{job_id}", response_model=JobRead, dependencies=[Depends(require_api_key)])
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, {"code": "not_found", "message": "Job not found"})
    return as_job(job)


@app.post("/jobs/{job_id}/run", response_model=JobRead, dependencies=[Depends(require_api_key)])
async def run_job(job_id: int, db: Session = Depends(get_db), client: ModelClient = Depends(client_dependency)) -> dict:
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, {"code": "not_found", "message": "Job not found"})
    prompt = redact(job.input_text)
    job.status = "running"; db.commit()
    started = time.perf_counter(); status = "success"
    try:
        job.result = await client.generate(f"Task: {job.job_type}\nInput: {prompt}")
        job.status = "completed"; job.error = None
    except Exception as exc:
        status = "failure"; job.status = "failed"; job.error = "Model request failed"
    finally:
        db.add(AuditLog(job_id=job.id, prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(), latency_ms=int((time.perf_counter()-started)*1000), status=status))
        db.commit(); db.refresh(job)
    return as_job(job)


@app.get("/audit", response_model=list[AuditRead], dependencies=[Depends(require_api_key)])
def audit(db: Session = Depends(get_db)) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)).all())

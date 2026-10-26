from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .config import MAX_INPUT_CHARS


class JobCreate(BaseModel):
    type: Literal["summarize", "classify", "extract"]
    input_text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    input_text: str
    status: str
    result: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    prompt_hash: str
    latency_ms: int
    status: str
    created_at: datetime

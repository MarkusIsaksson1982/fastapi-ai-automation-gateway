import hashlib
import hmac
from fastapi import Header, HTTPException
from .config import api_key_hashes


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not x_api_key:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid API key"})
    supplied = hashlib.sha256(x_api_key.encode()).hexdigest()
    if not any(hmac.compare_digest(supplied, expected) for expected in api_key_hashes()):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid API key"})

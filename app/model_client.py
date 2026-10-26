import httpx
from .config import MODEL_NAME, MODEL_TIMEOUT_SECONDS, OLLAMA_URL


class ModelClient:
    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{OLLAMA_URL.rstrip('/')}/api/generate", json={"model": MODEL_NAME, "prompt": prompt, "stream": False})
            response.raise_for_status()
            return response.json()["response"]

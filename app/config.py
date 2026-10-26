import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2")
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "10000"))
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "30"))


def api_key_hashes() -> list[str]:
    return [key.strip().lower() for key in os.getenv("API_KEYS", "").split(",") if key.strip()]

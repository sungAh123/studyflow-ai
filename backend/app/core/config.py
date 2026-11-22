import os


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"환경변수 {name}이 없음")
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/studyflow.db")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

NOTION_CLIENT_ID = _required("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = _required("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = _required("NOTION_REDIRECT_URI")
SESSION_SECRET = _required("SESSION_SECRET")
TOKEN_ENCRYPTION_KEY = _required("TOKEN_ENCRYPTION_KEY")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "100"))
MIN_TEXT_CHARS = int(os.getenv("MIN_TEXT_CHARS", "50"))

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "600"))
CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", "6000"))
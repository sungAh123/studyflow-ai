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
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/studyflow.db")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth import models as auth_models  # noqa: F401  (테이블 등록)
from app.auth.router import router as auth_router
from app.core.config import COOKIE_SECURE, CORS_ORIGINS, SESSION_SECRET
from app.core.db import Base, engine
from app.subjects import models as subject_models   # noqa: F401 (테이블 등록)
from app.subjects.router import router as subject_router
from app.documents import models as document_models  # noqa: F401  (테이블 등록)
from app.documents.router import router as documents_router
from app.summaries import models as summary_models  # noqa: F401  (테이블 등록)
from app.summaries.router import router as summaries_router

Base.metadata.create_all(bind=engine)


app = FastAPI(title="StudyFlow AI")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE,
    max_age=60 * 60 * 24 * 14,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(subject_router)
app.include_router(documents_router)
app.include_router(summaries_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
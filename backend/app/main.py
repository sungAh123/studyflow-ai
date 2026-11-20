from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS
from app.core.db import Base, engine
from app.subjects import models as subject_models   # noqa: F401 (테이블 등록)
from app.subjects.router import router as subject_router

Base.metadata.create_all(bind=engine)


app = FastAPI(title="StudyFlow AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subject_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
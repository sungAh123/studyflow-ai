from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user
from app.core.db import get_db
from app.documents.schemas import DocumentOut

from . import service
from .schemas import SummaryOut

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.post("/{document_id}", response_model=DocumentOut, status_code=202)
def start_summary(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        doc = service.start_summarization(db, user.id, document_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except service.SummaryError as e:
        raise HTTPException(400, str(e))
    background_tasks.add_task(service.run_summarization, doc.id)
    return doc


@router.get("/{document_id}", response_model=SummaryOut)
def get_summary (
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    summary = service.get_summary(db, user.id, document_id)
    if summary is None:
        raise HTTPException(404, "요약 결과가 없습니다.")
    return summary


@router.post("/{document_id}/cancel", response_model=DocumentOut, status_code=202)
def cancel_summary(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return service.request_cancel(db, user.id, document_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except service.SummaryError as e:
        raise HTTPException(400, str(e))
        
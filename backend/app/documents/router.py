from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user
from app.core.db import get_db

from . import service
from .schemas import DocumentDetail, DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(
    background_tasks: BackgroundTasks,
    subject_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        doc = service.save_upload(db, user.id, subject_id, file)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except service.UploadError as e:
        raise HTTPException(400, str(e))
    background_tasks.add_task(service.run_extraction, doc.id)
    return doc


@router.get("", response_model=list[DocumentOut])
def get_documents(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_documents(db, user.id, subject_id)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = service.get_document(db, user.id, document_id)
    if doc is None:
        raise HTTPException(404, "자료를 찾을 수 없습니다.")
    return doc


@router.delete("/{document_id}", status_code=204)
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not service.delete_document(db, user.id, document_id):
        raise HTTPException(404, "자료를 찾을 수 없습니다.")
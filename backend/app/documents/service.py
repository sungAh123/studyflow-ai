import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import MAX_UPLOAD_MB
from app.core.db import SessionLocal
from app.subjects import service as subjects_service
from app.subjects.models import Subject

from . import extractor
from .models import DocStatus, Document

logger = logging.getLogger("uvicorn.error")

UPLOAD_ROOT = Path("data/uploads")
MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024


class UploadError(Exception):
    """사용자에게 그대로 보여줄 수 있는 업로드 실패 사유."""


def save_upload(db: Session, user_id: int, subject_id: int, file: UploadFile) -> Document:
    if subjects_service.get_owned_subject(db, user_id, subject_id) is None:
        raise LookupError("과목을 찾을 수 없습니다.")

    name = Path(file.filename or "").name
    if not name.lower().endswith(".pdf"):
        raise UploadError("PDF 파일만 업로드할 수 있습니다.")
    if file.file.read(5) != b"%PDF-":
        raise UploadError("올바른 PDF 파일이 아닙니다.")
    file.file.seek(0)

    dest_dir = UPLOAD_ROOT / str(user_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex}.pdf"

    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := file.file.read(1024*1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise UploadError(f"파일 크기는 {MAX_UPLOAD_MB}MB 이하여야 합니다.")
                out.write(chunk)
    except UploadError:
        dest.unlink(missing_ok=True)
        raise

    doc = Document(subject_id=subject_id, filename=name[:255], stored_path=str(dest))
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session, user_id: int, subject_id: int | None = None) -> list[Document]:
    stmt = (
        select(Document)
        .join(Subject, Document.subject_id==Subject.id)
        .where(Subject.user_id==user_id)
        .order_by(Document.created_at.desc())
    )
    if subject_id is not None:
        stmt = stmt.where(Document.subject_id==subject_id)
    return list(db.scalars(stmt))


def get_document(db: Session, user_id: int, document_id: int) -> Document | None:
    return db.scalar(
        select(Document)
        .join(Subject, Document.subject_id==Subject.id)
        .where(Document.id==document_id, Subject.user_id==user_id)
    )


def delete_document(db: Session, user_id: int, document_id: int) -> bool:
    doc = get_document(db, user_id, document_id)
    if doc is None:
        return False
    Path(doc.stored_path).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()
    return True


def run_extraction(document_id: int) -> None:
    """백그라운드에서 실행되므로 요청 세션이 아닌 자체 세션을 사용한다."""
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        doc.status = DocStatus.EXTRACTING
        doc.error_message = None
        db.commit()

        try:
            pages = extractor.extract_pages(doc.stored_path)
        except extractor.ExtractionError as e:
            doc.status = DocStatus.FAILED
            doc.error_message = str(e)
        except Exception:
            logger.exception("문서 추출 중 예기치 않은 오류 (id=%s)", document_id)
            doc.status = DocStatus.FAILED
            doc.error_message = "처리 중 알 수 없는 오류가 발생했습니다."
        else:
            doc.pages_text = pages
            doc.page_count = len(pages)
            doc.status = DocStatus.EXTRACTED
        db.commit()


def get_for_processing(db: Session, document_id: int) -> Document | None:
    """백그라운드 작업용(소유자 확인 없음.) 요청 경로에서는 get_document를 씀"""
    return db.get(Document, document_id)


def set_status(db: Session, doc: Document, status: str, error: str | None = None) -> None:
    doc.status = status
    doc.error_message = error
    db.commit()
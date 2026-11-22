import logging

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.core.db import SessionLocal
from app.documents import service as documents_service
from app.documents.models import DocStatus, Document

from . import ollama
from .chunker import make_chunks
from .models import Summary
from .prompts import CHUNK_SYSTEM, REDUCE_SYSTEM
from .schemas import ChunkResult

logger = logging.getLogger("uvicorn.error")

STARTABLE = (DocStatus.EXTRACTED, DocStatus.DONE, DocStatus.FAILED)


class SummaryError(Exception):
    """사용자에게 그대로 보여줄 수 있는 요약 실패 사유."""


def start_summarization(db: Session, user_id: int, document_id: int) -> Document:
    doc = documents_service.get_document(db, user_id, document_id)
    if doc is None:
        raise LookupError("자료를 찾을 수 없습니다.")
    # page_count는 추출에 성공했을 때만 채워짐. 추출 실패 문서는 요약할 수 없다.
    if doc.status not in STARTABLE or not doc.pages_text:
        raise SummaryError("텍스트 추출이 끝난 자료만 요약할 수 있습니다.")
    documents_service.set_status(db, doc, DocStatus.SUMMARIZING)    # 중복 클릭 방지
    return doc


def get_summary(db: Session, user_id: int, document_id: int) -> Summary | None:
    doc = documents_service.get_document(db, user_id, document_id)
    if doc is None:
        return None
    return db.scalar(select(Summary).where(Summary.document_id==doc.id))


def summarize_pages(pages: list[str]) -> dict:
    chunks = make_chunks(pages, config.CHUNK_CHARS)
    if not chunks:
        raise SummaryError("요약할 텍스트가 없습니다.")

    partials: list[ChunkResult] = []
    for chunk in chunks:
        try:
            partials.append(ChunkResult.model_validate(ollama.chat_json(CHUNK_SYSTEM, chunk)))
        except ValidationError as e:
            raise SummaryError("AI 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.") from e

    if len(partials) == 1:
        overview = partials[0].summary
    else:
        joined = "\n\n".join(f"[{i}] {p.summary}" for i, p in enumerate(partials, 1))
        overview = str(ollama.chat_json(REDUCE_SYSTEM, joined).get("overview", "")).strip()
        if not overview:
            raise SummaryError("전체 요약을 만들지 못했습니다. 다시 시도해 주세요.")

    sections = [s.model_dump() for p in partials for s in p.sections]
    seen: set[str] = set()
    terms = []
    for p in partials:
        for t in p.terms:
            key = t.term.strip().lower()
            if key and key not in seen:
                seen.add(key)
                terms.append(t.model_dump())
    return {"overview": overview, "sections": sections, "terms": terms}


def run_summarization(document_id: int) -> None:
    """백그라운드에서 실행되므로 요청 세션이 아닌 자체 세션을 사용함"""
    with SessionLocal() as db:
        doc = documents_service.get_for_processing(db, document_id)
        if doc is None:
            return
        try:
            result = summarize_pages(doc.pages_text or [])
        except (SummaryError, ollama.LLMError) as e:
            documents_service.set_status(db, doc, DocStatus.FAILED, str(e))
            return
        except Exception:
            logger.exception("요약 중 예기치 않은 오류 (id=%s)", document_id)
            documents_service.set_status(
                db, doc, DocStatus.FAILED, "처리 중 알 수 없는 오류가 발생하였습니다."
            )
            return

        old = db.scalar(select(Summary).where(Summary.document_id==document_id))
        if old is not None:
            db.delete(old)
            db.flush()
        db.add(Summary(document_id=document_id, **result))
        documents_service.set_status(db, doc, DocStatus.DONE)
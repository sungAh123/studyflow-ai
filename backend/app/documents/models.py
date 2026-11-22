from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class DocStatus:
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    SUMMARIZING = "summarizing"
    DONE = "done"
    FAILED = "failed"
    CANCELLING = "cancelling"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=DocStatus.UPLOADED)
    error_message: Mapped[str | None] = mapped_column(String(255), default=None)
    page_count: Mapped[int | None] = mapped_column(default=None)
    pages_text: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    summary: Mapped["Summary | None"] = relationship(
            "Summary", cascade="all, delete-orphan", uselist=False
        )
    progress_done: Mapped[int] = mapped_column(default=0)
    progress_total: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), unique=True)
    overview: Mapped[str] = mapped_column(Text)
    sections: Mapped[list] = mapped_column(JSON)   # [{"title": str, "points": [str]}]
    terms: Mapped[list] = mapped_column(JSON)      # [{"term": str, "definition": str}]
    notion_page_id: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
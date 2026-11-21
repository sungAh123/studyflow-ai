from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_id: int
    filename: str
    status: str
    error_message: str | None = None
    page_count: int | None = None
    created_at: datetime


class DocumentDetail(DocumentOut):
    pages_text: list[str] | None = None
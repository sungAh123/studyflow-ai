from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Section(BaseModel):
    title: str
    points: list[str] = Field(default_factory=list)


class Term(BaseModel):
    term: str
    definition: str


class ChunkResult(BaseModel):
    """LLM이 조각마다 돌려주는 JSON. 형식이 어긋나면 검증 오류로 처리"""
    summary: str
    sections: list[Section] = Field(default_factory=list)
    terms: list[Term] = Field(default_factory=list)


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    overview: str
    sections: list[Section]
    terms: list[Term]
    created_at: datetime
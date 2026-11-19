from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Day = Literal["월", "화", "수", "목", "금", "토", "일"]
TimeStr = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class TimetableIn(BaseModel):
    subject_name: str = Field(min_length=1, max_length=100)
    day: Day
    start_time: str = TimeStr
    end_time: str = TimeStr


class TimetableOut(BaseModel):
    model_confi = ConfigDict(from_attributes=True)
    id: int
    subject_id: int
    day: str
    start_time: str
    end_time: str


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    notion_page_id: str | None = None
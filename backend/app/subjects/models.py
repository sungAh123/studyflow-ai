from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    notion_page_id: Mapped[str | None] = mapped_column(String(64), default=None)

    timetables: Mapped[list["Timetable"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    day: Mapped[str] = mapped_column(String(1))        # 월~일
    start_time: Mapped[str] = mapped_column(String(5))  # "09:00"
    end_time: Mapped[str] = mapped_column(String(5))

    Subject: Mapped[Subject] = relationship(back_populates="timetables")
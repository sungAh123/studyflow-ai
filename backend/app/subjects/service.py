from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Subject, Timetable
from .schemas import TimetableIn


def get_or_create_subject(db: Session, name: str) -> Subject:
    name = name.strip()
    subject = db.scalars(select(Subject).where(Subject.name==name))
    if subject is None:
        subject = Subject(name=name)
        db.add(subject)
        db.flush()
    return subject


def list_subjects(db: Session) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.name)))


def list_timetables(db: Session) -> list[Timetable]:
    return list(db.scalars(select(Timetable).order_by(Timetable.day, Timetable.start_time)))


def create_timetable(db: Session, data: TimetableIn) -> Timetable:
    subject = get_or_create_subject(db, data.subject_name)
    row = Timetable(
        subject_id=subject.id,
        day=data.day,
        start_time=data.start_time,
        end_time=data.end_time,
    ) 
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_timetable(db: Session, timetable_id: int, data: TimetableIn) -> Timetable | None:
    row = db.get(Timetable, timetable_id)
    if row is None:
        return None
    row.subject_id = get_or_create_subject(db, data.subject_name).id
    row.day = data.day
    row.start_time = data.start_time
    row.end_time = data.end_time
    db.commit()
    db.refresh(row)
    return row


def delete_timetable(db: Session, timetable_id: int) -> bool:
    row = db.get(Timetable, timetable_id)
    if row is None:
        return False
    
    db.delete(row)
    db.commit()
    return True
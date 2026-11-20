from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Subject, Timetable
from .schemas import TimetableIn


def get_or_create_subject(db: Session, user_id: int, name: str) -> Subject:
    name = name.strip()
    subject = db.scalars(
        select(Subject).where(Subject.user_id==user_id, Subject.name==name)
    ).first()
    if subject is None:
        subject = Subject(user_id=user_id, name=name)
        db.add(subject)
        db.flush()
    return subject


def list_subjects(db: Session, user_id: int) -> list[Subject]:
    return list(
        db.scalars(
            select(Subject).where(Subject.user_id==user_id).order_by(Subject.name)
        )
    )


def list_timetables(db: Session, user_id: int) -> list[Timetable]:
    return list(
        db.scalars(
            select(Timetable)
            .join(Subject)
            .where(Subject.user_id==user_id)
            .order_by(Timetable.day, Timetable.start_time)
        )
    )


def _get_owned_timetable(db: Session, user_id: int, timetable_id: int) -> Timetable | None:
    return db.scalar(
        select(Timetable)
        .join(Subject)
        .where(Timetable.id==timetable_id, Subject.user_id==user_id)
    )


def create_timetable(db: Session, user_id: int, data: TimetableIn) -> Timetable:
    subject = get_or_create_subject(db, user_id, data.subject_name)
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


def update_timetable(
    db: Session, user_id: int, timetable_id: int, data: TimetableIn
) -> Timetable | None:
    row = _get_owned_timetable(db, user_id, timetable_id)
    if row is None:
        return None
    row.subject_id = get_or_create_subject(db, user_id, data.subject_name).id
    row.day = data.day
    row.start_time = data.start_time
    row.end_time = data.end_time
    db.commit()
    db.refresh(row)
    return row


def delete_timetable(db: Session, user_id: int, timetable_id: int) -> bool:
    row = _get_owned_timetable(db, user_id, timetable_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
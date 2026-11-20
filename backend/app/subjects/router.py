from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from . import service
from .schemas import SubjectOut, TimetableIn, TimetableOut

router = APIRouter(prefix="/api", tags=["subjects"])


@router.get("/subjects", response_model=list[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    return service.list_subjects(db)


@router.get("/timetables", response_model=list[TimetableOut])
def get_timetables(db: Session = Depends(get_db)):
    return service.list_timetables(db)


@router.post("/timetables", response_model=TimetableOut, status_code=201)
def add_timetable(data: TimetableIn, db: Session = Depends(get_db)):
    return service.create_timetable(db, data)


@router.put("/timetables/{timetable_id}", response_model=TimetableOut)
def edit_timetable(timetable_id: int, data: TimetableIn, db: Session = Depends(get_db)):
    row = service.update_timetable(db, timetable_id, data)
    if row is None:
        raise HTTPException(404, "시간표를 찾을 수 없습니다.")
    return row


@router.delete("/timetables/{timetable_id}", status_code=204)
def remove_timetable(timetable_id: int, db: Session = Depends(get_db)):
    if not service.delete_timetable(db, timetable_id): 
        raise HTTPException(404, "시간표를 찾을 수 없습니다.")
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user
from app.core.db import get_db

from . import service
from .schemas import SubjectOut, TimetableIn, TimetableOut

router = APIRouter(prefix="/api", tags=["subjects"])


@router.get("/subjects", response_model=list[SubjectOut])
def get_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_subjects(db, user.id)


@router.get("/timetables", response_model=list[TimetableOut])
def get_timetables(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_timetables(db, user.id)


@router.post("/timetables", response_model=TimetableOut, status_code=201)
def add_timetable(
    data: TimetableIn, 
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_timetable(db, user.id, data)


@router.put("/timetables/{timetable_id}", response_model=TimetableOut)
def edit_timetable(
    timetable_id: int, 
    data: TimetableIn, 
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = service.update_timetable(db, user.id, timetable_id, data)
    if row is None:
        raise HTTPException(404, "시간표를 찾을 수 없습니다.")
    return row


@router.delete("/timetables/{timetable_id}", status_code=204)
def remove_timetable(
    timetable_id: int, 
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not service.delete_timetable(db, user.id, timetable_id): 
        raise HTTPException(404, "시간표를 찾을 수 없습니다.")
import secrets
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.db import get_db

from . import service
from .models import User
from .schemas import UserOut

import logging

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("uvicorn.error")

def _login_error(reason: str) -> RedirectResponse:
    return RedirectResponse(f"{FRONTEND_URL}/?login_error={quote(reason)}")


@router.get("/notion/login")
def notion_login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return RedirectResponse(service.build_authorize_url(state))


@router.get("/notion/callback")
def notion_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    expected_state = request.session.pop("oauth_state", None)
    if error or not code:
        return _login_error("denied")
    if not state or state != expected_state:
        raise HTTPException(400, "잘못된 로그인 요청입니다.")

    try:
        token_data = service.exchange_code(code)
        user = service.upsert_user(db, token_data)
    except httpx.HTTPStatusError as e:
        logger.error("Notion 토큰 교환 실패: %s %s", e.response.status_code, e.response.text)
        return _login_error("failed")
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.exception("로그인 처리 실패: %r", e)
        return _login_error("failed")

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(FRONTEND_URL)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(service.get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.session.clear()
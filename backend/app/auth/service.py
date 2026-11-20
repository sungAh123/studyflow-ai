from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.core.db import get_db
from app.core.security import encrypt

from .models import User

NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"


def build_authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": config.NOTION_CLIENT_ID,
            "response_type": "code",
            "owner": "user",
            "redirect_uri": config.NOTION_REDIRECT_URI,
            "state": state,
        }
    )
    return f"{NOTION_AUTH_URL}?{query}"


def exchange_code(code: str) -> dict:
    res = httpx.post(
        NOTION_TOKEN_URL,
        auth=(config.NOTION_CLIENT_ID, config.NOTION_CLIENT_SECRET),
        headers={"Notion-Version": "2022-06-28"},
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.NOTION_REDIRECT_URI,
        },
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def upsert_user(db: Session, token_data: dict) -> User:
    notion_user = (token_data.get("owner") or {}).get("user") or {}
    notion_user_id = notion_user.get("id")
    if not notion_user_id:
        raise ValueError("Notion 응답에 사용자 정보가 없습니다.")

    user = db.scalar(select(User).where(User.notion_user_id == notion_user_id))
    if user is None:
        user = User(notion_user_id=notion_user_id)
        db.add(user)

    user.name = notion_user.get("name")
    user.email = (notion_user.get("person") or {}).get("email")
    user.workspace_id = token_data.get("workspace_id")
    user.workspace_name = token_data.get("workspace_name")
    user.access_token_enc = encrypt(token_data["access_token"])
    db.commit()
    db.refresh(user)
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "로그인이 필요합니다.")
    return user
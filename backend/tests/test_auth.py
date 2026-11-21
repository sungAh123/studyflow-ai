from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy import func, select

from app.auth.models import User
from app.core.db import SessionLocal
from app.core.security import decrypt


def test_me_requires_login(anon_client):
    assert anon_client.get("/api/auth/me").status_code == 401


def test_login_redirects_to_notion_authorize(anon_client):
    res = anon_client.get("/api/auth/notion/login", follow_redirects=False)
    assert res.status_code == 307

    url = urlparse(res.headers["location"])
    assert url.netloc == "api.notion.com"
    assert url.path == "/v1/oauth/authorize"

    query = parse_qs(url.query)
    assert query["client_id"] == ["test-client-id"]
    assert query["redirect_uri"] == ["http://localhost:5173/api/auth/notion/callback"]
    assert query["response_type"] == ["code"]
    assert query["owner"] == ["user"]
    assert query["state"][0]


def test_callback_rejects_forged_state(anon_client):
    anon_client.get("/api/auth/notion/login", follow_redirects=False)
    res = anon_client.get(
        "/api/auth/notion/callback",
        params={"code": "c", "state": "forged"},
        follow_redirects=False,
    )
    assert res.status_code == 400


def test_callback_rejects_missing_session_state(anon_client):
    res = anon_client.get(
        "/api/auth/notion/callback",
        params={"code": "c", "state": "anything"},
        follow_redirects=False,
    )
    assert res.status_code == 400


def test_callback_user_denied(anon_client):
    res = anon_client.get(
        "/api/auth/notion/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert "login_error=denied" in res.headers["location"]


def test_callback_token_exchange_failure(anon_client, monkeypatch):
    def boom(code):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("app.auth.service.exchange_code", boom)

    res = anon_client.get("/api/auth/notion/login", follow_redirects=False)
    state = parse_qs(urlparse(res.headers["location"]).query)["state"][0]
    res = anon_client.get(
        "/api/auth/notion/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )

    assert res.status_code == 307
    assert "login_error=failed" in res.headers["location"]
    assert anon_client.get("/api/auth/me").status_code == 401


def test_callback_creates_user_and_session(anon_client, login):
    login(
        anon_client,
        notion_user_id="n-1",
        name="홍길동",
        email="hong@example.com",
        token="secret_abc",
    )

    me = anon_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["name"] == "홍길동"
    assert me.json()["email"] == "hong@example.com"
    assert me.json()["workspace_name"] == "테스트 워크스페이스"

    with SessionLocal() as db:
        user = db.scalar(select(User))
        assert user.notion_user_id == "n-1"
        assert user.access_token_enc != "secret_abc"  # 평문 저장 금지
        assert decrypt(user.access_token_enc) == "secret_abc"


def test_same_notion_user_logs_in_twice_keeps_one_row(make_client):
    make_client(notion_user_id="n-1", name="이전 이름")
    make_client(notion_user_id="n-1", name="바뀐 이름")

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(User)).name == "바뀐 이름"


def test_logout_clears_session(client):
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
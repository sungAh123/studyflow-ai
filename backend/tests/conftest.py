import os
import tempfile
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet

# app 모듈을 import하기 전에 설정해야 한다.
# 실제 .env 값이 들어와도 덮어써서 개발용 DB와 Notion 계정을 건드리지 않게 한다.
_TMP = tempfile.mkdtemp(prefix="studyflow-test-")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_TMP}/test.db",
        "NOTION_CLIENT_ID": "test-client-id",
        "NOTION_CLIENT_SECRET": "test-client-secret",
        "NOTION_REDIRECT_URI": "http://localhost:5173/api/auth/notion/callback",
        "FRONTEND_URL": "http://localhost:5173",
        "SESSION_SECRET": "test-session-secret",
        "TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    }
)

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    # 안전장치: 테스트용 임시 DB가 아니면 절대 테이블을 지우지 않는다.
    assert "studyflow-test-" in str(engine.url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    path = tmp_path / "uploads"
    monkeypatch.setattr("app.documents.service.UPLOAD_ROOT", path)
    return path


@pytest.fixture
def anon_client():
    return TestClient(app)


@pytest.fixture
def login(monkeypatch):
    """Notion 토큰 교환만 가짜로 대체하고, 로그인 흐름(state·세션 쿠키)은 실제로 거친다."""

    def _login(
        client,
        notion_user_id="notion-user-1",
        name="홍길동",
        email="user@example.com",
        token="secret_access_token",
    ):
        token_data = {
            "access_token": token,
            "workspace_id": "ws-1",
            "workspace_name": "테스트 워크스페이스",
            "owner": {
                "type": "user",
                "user": {
                    "id": notion_user_id,
                    "name": name,
                    "person": {"email": email},
                },
            },
        }
        monkeypatch.setattr("app.auth.service.exchange_code", lambda code: token_data)

        res = client.get("/api/auth/notion/login", follow_redirects=False)
        state = parse_qs(urlparse(res.headers["location"]).query)["state"][0]
        res = client.get(
            "/api/auth/notion/callback",
            params={"code": "dummy-code", "state": state},
            follow_redirects=False,
        )
        assert res.status_code == 307

    return _login


@pytest.fixture
def make_client(login):
    """로그인된 새 클라이언트(쿠키 저장소가 따로라 사용자별로 분리됨)를 만든다."""

    def _make(**user):
        client = TestClient(app)
        login(client, **user)
        return client

    return _make


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def make_subject():
    def _make(client, name="운영체제"):
        res = client.post(
            "/api/timetables",
            json={
                "subject_name": name,
                "day": "월",
                "start_time": "09:00",
                "end_time": "10:30",
            },
        )
        assert res.status_code == 201
        return res.json()["subject_id"]

    return _make


@pytest.fixture
def make_pdf():
    """pages: 쪽별 텍스트 목록. 빈 문자열이면 텍스트 없는 쪽(스캔본 흉내)."""

    def _make(pages, password=None):
        doc = pymupdf.open()
        for text in pages:
            page = doc.new_page()
            if text:
                page.insert_text((72, 72), text)
        if password:
            data = doc.tobytes(
                encryption=pymupdf.PDF_ENCRYPT_AES_256,
                user_pw=password,
                owner_pw=password,
            )
        else:
            data = doc.tobytes()
        doc.close()
        return data

    return _make


@pytest.fixture
def fake_llm(monkeypatch):
    """Ollama 호출을 가짜로 대체한다. calls에 (system, user)가 쌓이고, 응답은 순서대로 꺼낸다."""

    class FakeLLM:
        def __init__(self):
            self.calls = []
            self.responses = []  # dict는 그대로 반환, Exception은 raise

        def __call__(self, system, user):
            self.calls.append((system, user))
            if not self.responses:
                raise AssertionError("준비된 가짜 응답이 부족합니다.")
            item = self.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

    fake = FakeLLM()
    monkeypatch.setattr("app.summaries.ollama.chat_json", fake)
    return fake


@pytest.fixture
def chunk_json():
    """LLM이 조각마다 돌려주는 JSON을 흉내 내는 헬퍼."""

    def _make(summary="요약 문장", title="소주제", points=("핵심 1",), terms=()):
        return {
            "summary": summary,
            "sections": [{"title": title, "points": list(points)}],
            "terms": [{"term": t, "definition": d} for t, d in terms],
        }

    return _make


@pytest.fixture
def extracted_doc(make_subject, make_pdf):
    """업로드 + 추출까지 끝난 문서 ID를 만든다."""
    from tests.test_documents import TEXT, upload, wait_done

    def _make(client, pages=None, subject_name="운영체제"):
        subject_id = make_subject(client, subject_name)
        res = upload(client, subject_id, make_pdf(pages or [TEXT, TEXT]))
        doc = wait_done(client, res.json()["id"])
        assert doc["status"] == "extracted"
        return doc["id"]

    return _make


@pytest.fixture(autouse=True)
def extract_in_process(monkeypatch):
    """테스트에서는 별도 프로세스 대신 같은 프로세스에서 추출한다.
    (monkeypatch한 설정값이 자식 프로세스에는 전달되지 않기 때문)"""
    from app.documents import extractor

    monkeypatch.setattr("app.documents.service._extract", extractor.extract_pages)
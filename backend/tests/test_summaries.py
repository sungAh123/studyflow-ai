import pytest

from app.summaries.ollama import LLMError
from tests.test_documents import TEXT, upload, wait_done


def wait_summary(client, doc_id, timeout=5.0):
    """요약이 끝날 때(done/failed)까지 상태를 폴링한다."""
    import time

    deadline = time.monotonic() + timeout
    while True:
        doc = client.get(f"/api/documents/{doc_id}").json()
        if doc["status"] in ("done", "failed") or time.monotonic() > deadline:
            return doc
        time.sleep(0.05)


def summarize(client, doc_id):
    res = client.post(f"/api/summaries/{doc_id}")
    assert res.status_code == 202
    return wait_summary(client, doc_id)


def test_endpoints_require_login(anon_client):
    assert anon_client.post("/api/summaries/1").status_code == 401
    assert anon_client.get("/api/summaries/1").status_code == 401


def test_summarize_single_chunk(client, extracted_doc, fake_llm, chunk_json):
    doc_id = extracted_doc(client)
    fake_llm.responses = [
        chunk_json(
            summary="운영체제는 자원을 관리한다.",
            title="프로세스",
            points=("프로세스는 실행 중인 프로그램", "스케줄링으로 CPU 배분"),
            terms=[("PCB", "프로세스 제어 블록")],
        )
    ]

    doc = summarize(client, doc_id)

    assert doc["status"] == "done"
    assert doc["error_message"] is None
    assert len(fake_llm.calls) == 1  # 조각이 하나면 합치기 호출이 없다

    result = client.get(f"/api/summaries/{doc_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["overview"] == "운영체제는 자원을 관리한다."
    assert body["sections"][0]["title"] == "프로세스"
    assert len(body["sections"][0]["points"]) == 2
    assert body["terms"] == [{"term": "PCB", "definition": "프로세스 제어 블록"}]


def test_summarize_multiple_chunks_runs_reduce_step(
    client, extracted_doc, fake_llm, chunk_json, monkeypatch
):
    monkeypatch.setattr("app.core.config.CHUNK_CHARS", 100)
    pages = ["가" * 80, "나" * 80, "다" * 80]
    doc_id = extracted_doc(client, pages=pages)
    # PDF 폰트 영향 없이 3개 조각이 나오도록 추출 결과를 직접 지정
    from app.core.db import SessionLocal
    from app.documents.models import Document

    with SessionLocal() as db:
        db.get(Document, doc_id).pages_text = pages
        db.commit()

    fake_llm.responses = [
        chunk_json(summary="조각1", title="A", terms=[("스레드", "실행 단위")]),
        chunk_json(summary="조각2", title="B", terms=[("스레드", "중복 용어")]),
        chunk_json(summary="조각3", title="C"),
        {"overview": "전체를 합친 요약"},
    ]

    doc = summarize(client, doc_id)

    assert doc["status"] == "done"
    assert len(fake_llm.calls) == 4  # 조각 3 + 합치기 1

    reduce_system, reduce_input = fake_llm.calls[-1]
    assert "조각1" in reduce_input and "조각3" in reduce_input

    body = client.get(f"/api/summaries/{doc_id}").json()
    assert body["overview"] == "전체를 합친 요약"
    assert [s["title"] for s in body["sections"]] == ["A", "B", "C"]
    # 같은 용어는 한 번만 남는다(먼저 나온 설명 유지)
    assert body["terms"] == [{"term": "스레드", "definition": "실행 단위"}]


def test_status_is_summarizing_right_after_start(
    client, extracted_doc, fake_llm, chunk_json, monkeypatch
):
    doc_id = extracted_doc(client)
    # 백그라운드 실행을 막아 "요약 중" 상태를 그대로 관찰한다.
    monkeypatch.setattr("app.summaries.service.run_summarization", lambda document_id: None)

    res = client.post(f"/api/summaries/{doc_id}")

    assert res.status_code == 202
    assert res.json()["status"] == "summarizing"
    assert client.get(f"/api/documents/{doc_id}").json()["status"] == "summarizing"


def test_cannot_start_while_summarizing(client, extracted_doc, monkeypatch):
    doc_id = extracted_doc(client)
    monkeypatch.setattr("app.summaries.service.run_summarization", lambda document_id: None)
    client.post(f"/api/summaries/{doc_id}")

    res = client.post(f"/api/summaries/{doc_id}")

    assert res.status_code == 400
    assert "추출이 끝난" in res.json()["detail"]


def test_cannot_summarize_failed_extraction(client, make_subject, make_pdf):
    subject_id = make_subject(client)
    res = upload(client, subject_id, make_pdf([""]))  # 스캔본 → 추출 실패
    doc = wait_done(client, res.json()["id"])
    assert doc["status"] == "failed"

    res = client.post(f"/api/summaries/{doc['id']}")

    assert res.status_code == 400


def test_summarize_missing_document_returns_404(client):
    assert client.post("/api/summaries/9999").status_code == 404


def test_get_summary_before_summarizing_returns_404(client, extracted_doc):
    doc_id = extracted_doc(client)

    assert client.get(f"/api/summaries/{doc_id}").status_code == 404


@pytest.mark.parametrize(
    "error, expected",
    [
        (LLMError("AI 서버(Ollama)에 연결할 수 없습니다."), "연결할 수 없습니다"),
        (RuntimeError("예상 못한 오류"), "알 수 없는 오류"),
    ],
)
def test_llm_failure_marks_document_failed(
    client, extracted_doc, fake_llm, error, expected
):
    doc_id = extracted_doc(client)
    fake_llm.responses = [error]

    doc = summarize(client, doc_id)

    assert doc["status"] == "failed"
    assert expected in doc["error_message"]
    assert client.get(f"/api/summaries/{doc_id}").status_code == 404


def test_malformed_llm_response_marks_document_failed(client, extracted_doc, fake_llm):
    doc_id = extracted_doc(client)
    fake_llm.responses = [{"unexpected": "형식이 다름"}]  # summary 필드 없음

    doc = summarize(client, doc_id)

    assert doc["status"] == "failed"
    assert "형식" in doc["error_message"]


def test_retry_after_failure_succeeds(client, extracted_doc, fake_llm, chunk_json):
    doc_id = extracted_doc(client)
    fake_llm.responses = [LLMError("일시적 오류")]
    assert summarize(client, doc_id)["status"] == "failed"

    fake_llm.responses = [chunk_json(summary="재시도 성공")]
    doc = summarize(client, doc_id)

    assert doc["status"] == "done"
    assert doc["error_message"] is None
    assert client.get(f"/api/summaries/{doc_id}").json()["overview"] == "재시도 성공"


def test_resummarize_replaces_previous_result(client, extracted_doc, fake_llm, chunk_json):
    doc_id = extracted_doc(client)
    fake_llm.responses = [chunk_json(summary="처음 요약")]
    summarize(client, doc_id)

    fake_llm.responses = [chunk_json(summary="다시 만든 요약")]
    doc = summarize(client, doc_id)

    assert doc["status"] == "done"
    assert client.get(f"/api/summaries/{doc_id}").json()["overview"] == "다시 만든 요약"

    from sqlalchemy import func, select

    from app.core.db import SessionLocal
    from app.summaries.models import Summary

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Summary)) == 1


def test_deleting_document_is_still_possible_after_summary(
    client, extracted_doc, fake_llm, chunk_json
):
    doc_id = extracted_doc(client)
    fake_llm.responses = [chunk_json()]
    summarize(client, doc_id)

    assert client.delete(f"/api/documents/{doc_id}").status_code == 204


def test_other_user_cannot_access_summary(
    client, make_client, extracted_doc, fake_llm, chunk_json
):
    doc_id = extracted_doc(client)
    fake_llm.responses = [chunk_json()]
    summarize(client, doc_id)
    other = make_client(notion_user_id="notion-user-2", name="김철수")

    assert other.get(f"/api/summaries/{doc_id}").status_code == 404
    assert other.post(f"/api/summaries/{doc_id}").status_code == 404

    assert client.get(f"/api/summaries/{doc_id}").status_code == 200


def test_deleting_document_also_deletes_summary(
    client, extracted_doc, fake_llm, chunk_json
):
    from sqlalchemy import func, select

    from app.core.db import SessionLocal
    from app.summaries.models import Summary

    doc_id = extracted_doc(client)
    fake_llm.responses = [chunk_json()]
    summarize(client, doc_id)

    assert client.delete(f"/api/documents/{doc_id}").status_code == 204

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Summary)) == 0
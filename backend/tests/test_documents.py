import time
import pytest

from app.core.db import SessionLocal
from app.documents import service as documents_service
from app.documents.models import DocStatus, Document


TEXT = "\n".join(f"Operating system lecture notes line {i}" for i in range(5))


def upload(client, subject_id, data, filename="lecture.pdf"):
    return client.post(
        "/api/documents",
        data={"subject_id": str(subject_id)},
        files={"file": (filename, data, "application/pdf")},
    )


def wait_done(client, doc_id, timeout=5.0):
    """추출이 끝날 때(extracted/failed)까지 상태를 폴링한다."""
    deadline = time.monotonic() + timeout
    while True:
        doc = client.get(f"/api/documents/{doc_id}").json()
        if doc["status"] in ("extracted", "failed") or time.monotonic() > deadline:
            return doc
        time.sleep(0.05)


def upload_and_fetch(client, subject_id, data, filename="lecture.pdf"):
    res = upload(client, subject_id, data, filename)
    assert res.status_code == 201
    return wait_done(client, res.json()["id"])


def test_endpoints_require_login(anon_client):
    assert anon_client.get("/api/documents").status_code == 401
    assert anon_client.get("/api/documents/1").status_code == 401
    assert anon_client.delete("/api/documents/1").status_code == 401
    res = anon_client.post(
        "/api/documents",
        data={"subject_id": "1"},
        files={"file": ("a.pdf", b"%PDF-", "application/pdf")},
    )
    assert res.status_code == 401


def test_upload_extracts_text_per_page(client, make_subject, make_pdf):
    subject_id = make_subject(client)

    doc = upload_and_fetch(client, subject_id, make_pdf([TEXT, TEXT]))

    assert doc["status"] == "extracted"
    assert doc["page_count"] == 2
    assert len(doc["pages_text"]) == 2
    assert "lecture notes" in doc["pages_text"][0]
    assert doc["error_message"] is None


def test_upload_to_missing_subject_returns_404(client, make_pdf):
    assert upload(client, 9999, make_pdf([TEXT])).status_code == 404


def test_non_pdf_extension_is_rejected(client, make_subject):
    subject_id = make_subject(client)

    res = upload(client, subject_id, b"hello", filename="notes.txt")

    assert res.status_code == 400
    assert "PDF 파일만" in res.json()["detail"]


def test_fake_pdf_is_rejected(client, make_subject):
    subject_id = make_subject(client)

    res = upload(client, subject_id, b"hello world", filename="fake.pdf")

    assert res.status_code == 400
    assert "올바른 PDF" in res.json()["detail"]


def test_oversized_file_is_rejected_and_not_kept(
    client, make_subject, make_pdf, monkeypatch, upload_dir
):
    monkeypatch.setattr("app.documents.service.MAX_BYTES", 100)
    subject_id = make_subject(client)

    res = upload(client, subject_id, make_pdf([TEXT]))

    assert res.status_code == 400
    assert "MB" in res.json()["detail"]
    assert list(upload_dir.rglob("*.pdf")) == []
    assert client.get("/api/documents").json() == []


def test_scanned_pdf_without_text_fails(client, make_subject, make_pdf):
    subject_id = make_subject(client)

    doc = upload_and_fetch(client, subject_id, make_pdf([""]))

    assert doc["status"] == "failed"
    assert "스캔본" in doc["error_message"]


def test_too_many_pages_fails(client, make_subject, make_pdf, monkeypatch):
    monkeypatch.setattr("app.documents.extractor.MAX_PAGES", 2)
    subject_id = make_subject(client)

    doc = upload_and_fetch(client, subject_id, make_pdf([TEXT, TEXT, TEXT]))

    assert doc["status"] == "failed"
    assert "2쪽" in doc["error_message"]


def test_encrypted_pdf_fails(client, make_subject, make_pdf):
    subject_id = make_subject(client)

    doc = upload_and_fetch(client, subject_id, make_pdf([TEXT], password="pw1234"))

    assert doc["status"] == "failed"
    assert "암호" in doc["error_message"]


def test_corrupted_pdf_fails(client, make_subject):
    subject_id = make_subject(client)

    doc = upload_and_fetch(client, subject_id, b"%PDF-1.4\nthis is not a real pdf")

    assert doc["status"] == "failed"
    assert doc["error_message"]


def test_filename_path_is_stripped(client, make_subject, make_pdf, upload_dir):
    subject_id = make_subject(client)

    doc = upload_and_fetch(client, subject_id, make_pdf([TEXT]), filename="../../evil.pdf")

    assert doc["filename"] == "evil.pdf"
    stored = list(upload_dir.rglob("*.pdf"))
    assert len(stored) == 1
    assert upload_dir in stored[0].parents


def test_list_can_filter_by_subject(client, make_subject, make_pdf):
    os_id = make_subject(client, "운영체제")
    db_id = make_subject(client, "데이터베이스")
    wait_done(client, upload(client, os_id, make_pdf([TEXT])).json()["id"])
    wait_done(client, upload(client, db_id, make_pdf([TEXT])).json()["id"])

    assert len(client.get("/api/documents").json()) == 2

    only = client.get("/api/documents", params={"subject_id": os_id}).json()
    assert len(only) == 1
    assert only[0]["subject_id"] == os_id

def test_delete_removes_record_and_file(client, make_subject, make_pdf, upload_dir):
    subject_id = make_subject(client)
    doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, doc_id)
    assert len(list(upload_dir.rglob("*.pdf"))) == 1

    assert client.delete(f"/api/documents/{doc_id}").status_code == 204

    assert client.get(f"/api/documents/{doc_id}").status_code == 404
    assert list(upload_dir.rglob("*.pdf")) == []


def test_delete_missing_document_returns_404(client):
    assert client.delete("/api/documents/9999").status_code == 404


def test_other_user_cannot_access_documents(client, make_client, make_subject, make_pdf):
    subject_id = make_subject(client)
    doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, doc_id)
    other = make_client(notion_user_id="notion-user-2", name="김철수")

    assert other.get("/api/documents").json() == []
    assert other.get(f"/api/documents/{doc_id}").status_code == 404
    assert other.delete(f"/api/documents/{doc_id}").status_code == 404
    # 남의 과목에는 업로드할 수 없다.
    assert upload(other, subject_id, make_pdf([TEXT])).status_code == 404

    assert client.get(f"/api/documents/{doc_id}").status_code == 200


def force_status(doc_id, status, **fields):
    """테스트에서 문서를 원하는 상태로 직접 만든다."""
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        doc.status = status
        for key, value in fields.items():
            setattr(doc, key, value)
        db.commit()


@pytest.mark.parametrize(
    "status",
    [DocStatus.UPLOADED, DocStatus.EXTRACTING, DocStatus.SUMMARIZING, DocStatus.CANCELLING],
)
def test_delete_is_blocked_while_processing(client, make_subject, make_pdf, status):
    subject_id = make_subject(client)
    doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, doc_id)
    force_status(doc_id, status)

    res = client.delete(f"/api/documents/{doc_id}")

    assert res.status_code == 409
    assert client.get(f"/api/documents/{doc_id}").status_code == 200

    force_status(doc_id, DocStatus.EXTRACTED)
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204


def test_reextract_failed_document(client, make_subject, make_pdf):
    subject_id = make_subject(client)
    doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, doc_id)
    force_status(
        doc_id, DocStatus.FAILED,
        pages_text=None, page_count=None, error_message="서버가 재시작되어 중단",
    )

    res = client.post(f"/api/documents/{doc_id}/extract")

    assert res.status_code == 202
    doc = wait_done(client, doc_id)
    assert doc["status"] == "extracted"
    assert doc["error_message"] is None
    assert doc["page_count"] == 1


def test_reextract_rejects_non_failed_document(client, make_subject, make_pdf):
    subject_id = make_subject(client)
    doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, doc_id)

    assert client.post(f"/api/documents/{doc_id}/extract").status_code == 409


def test_reextract_is_scoped_to_owner(client, make_client, make_subject, make_pdf):
    subject_id = make_subject(client)
    doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, doc_id)
    force_status(doc_id, DocStatus.FAILED)
    other = make_client(notion_user_id="notion-user-2", name="김철수")

    assert other.post(f"/api/documents/{doc_id}/extract").status_code == 404
    assert client.post("/api/documents/9999/extract").status_code == 404


def test_recover_interrupted_marks_busy_documents_failed(client, make_subject, make_pdf):
    subject_id = make_subject(client)
    ids = {}
    for status in (DocStatus.EXTRACTING, DocStatus.SUMMARIZING, DocStatus.CANCELLING):
        doc_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
        wait_done(client, doc_id)
        force_status(doc_id, status, progress_done=1, progress_total=3)
        ids[status] = doc_id
    done_id = upload(client, subject_id, make_pdf([TEXT])).json()["id"]
    wait_done(client, done_id)  # extracted 상태는 건드리면 안 된다

    with SessionLocal() as db:
        assert documents_service.recover_interrupted(db) == 3

    for doc_id in ids.values():
        doc = client.get(f"/api/documents/{doc_id}").json()
        assert doc["status"] == "failed"
        assert "재시작" in doc["error_message"]
        assert doc["progress_done"] == 0
    assert client.get(f"/api/documents/{done_id}").json()["status"] == "extracted"
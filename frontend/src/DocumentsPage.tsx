import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { api, ApiError } from "./api";
import type { DocStatus, DocumentDetail, DocumentItem, Subject, SummaryResult } from "./types";

const STATUS_LABEL: Record<DocStatus, string> = {
  uploaded: "업로드됨",
  extracting: "추출 중",
  extracted: "추출 완료",
  summarizing: "요약 중",
  done: "요약 완료",
  failed: "실패",
};

interface Props {
  onUnauthorized: () => void;
}

export default function DocumentsPage({ onUnauthorized }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState<SummaryResult | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const handleError = (e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
        onUnauthorized();
        return;
    }
    setError((e as Error).message);
  };

  const loadDocuments = async () => {
    try {
        setDocuments(await api<DocumentItem[]>("/documents"));
    } catch (e) {
        handleError(e);
    }
  };

  useEffect(() => {
    (async () => {
        try {
            const s = await api<Subject[]>("/subjects");
            setSubjects(s);
            if (s.length > 0) setSubjectId(String(s[0].id));
            await loadDocuments();
        } catch (e) {
            handleError(e);
        }
    })();
  }, []);

  //처리 중인 문서가 있으면 2초마다 상태 다시 조회
  const inProgress = documents.some(
    (d) => d.status === "uploaded" || d.status === "extracting" || d.status === "summarizing"
  );
  useEffect(() => {
    if (!inProgress) return;
    const timer = setTimeout(loadDocuments, 2000);
    return () => clearTimeout(timer);
  }, [inProgress, documents]);

  const subjectName = (id: number) => subjects.find((s) => s.id === id)?.name ?? "";

  const upload = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    if (!file || !subjectId) return;

    const body = new FormData();
    body.append("subject_id", subjectId);
    body.append("file", file);
    try {
      await api("/documents", { method: "POST", body });
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await loadDocuments();
    } catch (e) {
      handleError(e);
    }
  };

  const view = async (id: number) => {
    setError("");
      try {
        setDetail(await api<DocumentDetail>(`/documents/${id}`));
      } catch (e) {
        handleError(e);
      }
  };

  const remove = async (id: number) => {
    setError("");
    try {
      await api(`/documents/${id}`, { method: "DELETE" });
      await loadDocuments();
    } catch (e) {
      handleError(e);
    }
  };

  const summarize = async (id: number) => {
    setError("");
    try {
      await api(`/summaries/${id}`, {method: "POST"});
      setSummary(null);
      await loadDocuments();
    } catch (e) {
      handleError(e);
    }
  };

  const viewSummary = async (id: number) => {
    setError("");
    try {
      setSummary(await api<SummaryResult>(`/summaries/${id}`));
    } catch (e) {
      handleError(e);
    }
  };

  return (
<section>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>강의 자료 업로드</h2>
      {subjects.length === 0 ? (
        <p>먼저 시간표를 등록해서 과목을 만들어 주세요.</p>
      ) : (
        <form onSubmit={upload} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <input
            ref={fileInput}
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
          <button type="submit" disabled={!file}>업로드</button>
        </form>
      )}

      <h2>자료 목록 ({documents.length})</h2>
      <ul>
        {documents.map((d) => (
          <li key={d.id}>
            [{subjectName(d.subject_id)}] {d.filename} · {STATUS_LABEL[d.status]}
            {d.page_count !== null && ` (${d.page_count}쪽)`}
            {d.error_message && (
              <span style={{ color: "crimson" }}> — {d.error_message}</span>
            )}{" "}
            {d.page_count !== null && d.status !== "summarizing" && (
              <>
                <button onClick={() => view(d.id)}>텍스트 보기</button>{" "}
                <button onClick={() => summarize(d.id)}>
                  {d.status === "done" ? "다시 요약" : "요약하기"}
                </button>{" "}
              </>
            )}
            {d.status === "summarizing" && d.progress_total > 0 && (
              <> ({Math.round((d.progress_done / d.progress_total) * 100)}%)</>
            )}
            {d.status === "done" && (
              <button onClick={() => viewSummary(d.id)}>요약 보기</button>
            )}{" "}
            <button onClick={() => remove(d.id)}>삭제</button>
          </li>
        ))}
      </ul>

      {detail && (
        <>
          <h2>추출 텍스트: {detail.filename}</h2>
          <button onClick={() => setDetail(null)}>닫기</button>
          {detail.pages_text?.map((text, i) => (
            <div key={i}>
              <h4>{i + 1}쪽</h4>
              <pre style={{ whiteSpace: "pre-wrap", background: "#f5f5f5", padding: 8 }}>
                {text || "(텍스트 없음)"}
              </pre>
            </div>
          ))}
        </>
      )}

      {summary && (
        <>
          <h2>요약 미리보기</h2>
          <button onClick={() => setSummary(null)}>닫기</button>
          <h3>전체 요약</h3>
          <p>{summary.overview}</p>
          <h3>목차별 핵심</h3>
          {summary.sections.map((s, i) => (
            <div key={i}>
              <h4>{s.title}</h4>
              <ul>{s.points.map((p, j) => <li key={j}>{p}</li>)}</ul>
            </div>
          ))}
          <h3>주요 용어</h3>
          <ul>
            {summary.terms.map((t, i) => (
              <li key={i}><b>{t.term}</b>: {t.definition}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
const MESSAGES: Record<string, string> = {
    denied: "Notion 로그인이 취소되었습니다.",
    failed: "로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.",
};

export default function LoingPage() {
    const reason = new URLSearchParams(window.location.search).get("login_error");

    return (
    <main style={{ maxWidth: 420, margin: "6rem auto", textAlign: "center", fontFamily: "sans-serif" }}>
      <h1>StudyFlow AI</h1>
      <p>시간표 기반 강의 자료 자동 정리 서비스</p>
      {reason && (
        <p style={{ color: "crimson" }}>{MESSAGES[reason] ?? "로그인 중 오류가 발생했습니다."}</p>
      )}
      <a href="/api/auth/notion/login">
        <button type="button">Notion으로 로그인</button>
      </a>
    </main>
  );
}
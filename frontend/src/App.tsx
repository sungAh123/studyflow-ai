import { useEffect, useState } from "react";
import { api } from "./api";
import DocumentsPage from "./DocumentsPage";
import LoginPage from "./LoginPage";
import TimetablePage from "./TimetablePage";
import type { User } from "./types";

type Tab = "timetable" | "documents";
 
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<Tab>("timetable");

  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  const logout = async () => {
    await api("/auth/logout", { method: "POST" });
    setUser(null);
  };

  if (checking) return <p style={{ textAlign: "center" }}>불러오는 중...</p>;
  if (!user) return <LoginPage />;

  const onUnauthorized = () => setUser(null);

  return (
    <main style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>StudyFlow AI</h1>
        <div>
          {user.name ?? user.email ?? "사용자"}
          {user.workspace_name && ` (${user.workspace_name})`}{" "}
          <button onClick={logout}>로그아웃</button>
        </div>
      </header>

      <nav style={{ display: "flex", gap: 8 }}>
         <button onClick={() => setTab("timetable")} disabled={tab === "timetable"}>
          시간표
        </button>
        <button onClick={() => setTab("documents")} disabled={tab === "documents"}>
          강의 자료
        </button>
      </nav>
      
      {tab === "timetable" ? (
        <TimetablePage onUnauthorized={onUnauthorized} />
      ) : (
        <DocumentsPage onUnauthorized={onUnauthorized} />
      )}
    </main>
  );
}
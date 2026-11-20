import { useEffect, useState } from "react";
import { api } from "./api";
import LoginPage from "./LoginPage";
import TimetablePage from "./TimetablePage";
import type { User } from "./types";
 
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

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
      <TimetablePage onUnauthorized={() => setUser(null)} />
    </main>
  );
}
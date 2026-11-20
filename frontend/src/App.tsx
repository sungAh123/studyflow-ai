import { useEffect, useState, type ChangeEvent, type SyntheticEvent } from "react";

type Day = "월" | "화" | "수" | "목" | "금" | "토" | "일";

interface Subject {
  id: number;
  name: string;
  notion_page_id: string | null;
}

interface Timetable {
  id: number;
  subject_id: number;
  day: Day;
  start_time: string;
  end_time: string;
}

interface TimetableForm {
  subject_name: string;
  day: Day;
  start_time: string;
  end_time: string;
}

const DAYS: Day[] = ["월", "화", "수", "목", "금", "토", "일"];
const EMPTY: TimetableForm = {
  subject_name: "",
  day: "월",
  start_time: "09:00",
  end_time: "10:30",
};

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`요청 실패 (${res.status})`);
  return (res.status === 204 ? null : await res.json()) as T;
}


export default function App() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [form, setForm] = useState<TimetableForm>(EMPTY);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [s, t] = await Promise.all([
        api<Subject[]>("/subjects"),
        api<Timetable[]>("/timetables"),
      ]);
      setSubjects(s);
      setTimetables(t);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    try {
      await api("/timetables", {method: "POST", body: JSON.stringify(form)});
      setForm({...EMPTY, day: form.day});
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async (id: number) => {
    await api(`/timetables/${id}`, {method: "DELETE"});
    load();
  };

  const nameOf = (id: number) => subjects.find((s) => s.id === id)?.name ?? "";

  const set = 
    (key: keyof TimetableForm) =>
    (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm({...form, [key]: e.target.value});

    return (
      <main style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "sans-serif" }}>
        <h1>StudyFlow AI</h1>
        {error && <p style={{ color: "crimson" }}>{error}</p>}

        <h2>시간표 등록</h2>
        <form onSubmit={submit} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input placeholder="과목명" value={form.subject_name} onChange={set("subject_name")} required />
          <select value={form.day} onChange={set("day")}>
            {DAYS.map((d) => <option key={d}>{d}</option>)}
          </select>
          <input type="time" value={form.start_time} onChange={set("start_time")} required />
          <input type="time" value={form.end_time} onChange={set("end_time")} required />
          <button type="submit">등록</button>
        </form>

        <h2>과목 목록 ({subjects.length})</h2>
        <ul>{subjects.map((s) => <li key={s.id}>{s.name}</li>)}</ul>

        <h2>시간표</h2>
        <ul>
          {timetables.map((t) => (
            <li key={t.id}>
              {t.day} {t.start_time}~{t.end_time} · {nameOf(t.subject_id)}{" "}
              <button onClick={() => remove(t.id)}>삭제</button>
            </li>
          ))}
        </ul>
    </main>
  );
}
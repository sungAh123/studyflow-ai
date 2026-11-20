import { useEffect, useState, type ChangeEvent, type SyntheticEvent } from "react";
import { api, ApiError } from "./api";
import type { Day, Subject, Timetable, TimetableForm } from "./types";

const DAYS: Day[] = ["월", "화", "수", "목", "금", "토", "일"];
const EMPTY: TimetableForm = {
  subject_name: "",
  day: "월",
  start_time: "09:00",
  end_time: "10:30",
};

interface Props {
    onUnauthorized: () => void;
}

export default function TimetablePage({ onUnauthorized }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [form, setForm] = useState<TimetableForm>(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const handleError = (e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
        onUnauthorized();
        return;
    }
    setError((e as Error).message);
  };

  const load = async () => {
    try {
      const [s, t] = await Promise.all([
        api<Subject[]>("/subjects"),
        api<Timetable[]>("/timetables"),
      ]);
      setSubjects(s);
      setTimetables(t);
    } catch (e) {
      handleError(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const nameOf = (id: number) => subjects.find((s) => s.id === id)?.name ?? "";

  const startEdit = (t: Timetable) => {
    setEditingId(t.id);
    setForm({
      subject_name: nameOf(t.subject_id),
      day: t.day,
      start_time: t.start_time,
      end_time: t.end_time,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(EMPTY);
  }

  const submit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    try {
      if (editingId === null) {
        await api("/timetables", {method: "POST", body: JSON.stringify(form)});
        setForm({...EMPTY, day: form.day});
      } else {
        await api(`/timetables/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(form),
        });
        cancelEdit();
      }
      load();
    } catch (e) {
      handleError(e);
    }
  };

  const remove = async (id: number) => {
    setError("");
    try {
      await api(`/timetables/${id}`, {method: "DELETE"});
      if (editingId === id) cancelEdit();
      load();
    } catch(e) {
        handleError(e);
    }
  };

  const set = 
    (key: keyof TimetableForm) =>
    (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm({...form, [key]: e.target.value});

    return (
      <section>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>{editingId === null ? "시간표 등록" : "시간표 수정"}</h2>
      <form onSubmit={submit} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input placeholder="과목명" value={form.subject_name} onChange={set("subject_name")} required />
        <select value={form.day} onChange={set("day")}>
          {DAYS.map((d) => <option key={d}>{d}</option>)}
        </select>
        <input type="time" value={form.start_time} onChange={set("start_time")} required />
        <input type="time" value={form.end_time} onChange={set("end_time")} required />
        <button type="submit">{editingId === null ? "등록" : "저장"}</button>
        {editingId !== null && (
          <button type="button" onClick={cancelEdit}>취소</button>
        )}
      </form>

      <h2>과목 목록 ({subjects.length})</h2>
      <ul>{subjects.map((s) => <li key={s.id}>{s.name}</li>)}</ul>

      <h2>시간표</h2>
      <ul>
        {timetables.map((t) => (
          <li key={t.id} style={{ fontWeight: t.id === editingId ? "bold" : "normal" }}>
            {t.day} {t.start_time}~{t.end_time} · {nameOf(t.subject_id)}{" "}
            <button onClick={() => startEdit(t)}>수정</button>{" "}
            <button onClick={() => remove(t.id)}>삭제</button>
          </li>
        ))}
      </ul>
    </section>
  );
}
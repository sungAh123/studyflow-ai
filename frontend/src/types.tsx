export type Day = "월" | "화" | "수" | "목" | "금" | "토" | "일";
export type DocStatus = "uploaded" | "extracting" | "extracted" | "failed";

export interface User {
  id: number;
  name: string | null;
  email: string | null;
  workspace_name: string | null;
}

export interface Subject {
  id: number;
  name: string;
  notion_page_id: string | null;
}

export interface Timetable {
  id: number;
  subject_id: number;
  day: Day;
  start_time: string;
  end_time: string;
}

export interface TimetableForm {
  subject_name: string;
  day: Day;
  start_time: string;
  end_time: string;
}

export interface DocumentItem {
  id: number;
  subject_id: number;
  filename: string;
  status: DocStatus;
  error_message: string | null;
  page_count: number | null;
  created_at: string;
}

export interface DocumentDetail extends DocumentItem {
  pages_text: string[] | null;
}
export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message)
        this.status = status;
    }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`요청 실패 (${res.status})`);
  return (res.status === 204 ? null : await res.json()) as T;
}
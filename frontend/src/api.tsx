export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message)
        this.status = status;
    }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`/api${path}`, { ...options, headers });
  if (!res.ok) {
    let message = `요청 실패 (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // JSON 본문이 없으면 기본 메시지 사용
    }
    throw new ApiError(res.status, message);
  }
  return (res.status === 204 ? null : await res.json()) as T;
}
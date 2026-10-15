const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (init.method && !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase())) {
    headers.set("X-Requested-With", "FinSight");
  }
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const message =
      typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export type User = { id: string; email: string };
export type Transaction = {
  id: string; date: string; description: string; amount: string; currency: string;
  direction: "debit" | "credit"; tx_type: string; category: string; category_source: string;
};
export type Overview = {
  income: string; expenses: string; net_cash_flow: string; savings_rate: string | null;
  transaction_count: number; by_category: Record<string, string>;
};
export type ImportRow = {
  line: number; status: string; errors: string[]; date?: string; description?: string;
  amount?: string; direction?: "debit" | "credit"; category?: string; tx_type?: string;
};
export type ImportPreview = {
  id: string; status: string; source_type: string; confidence?: string; warnings: string[]; rows: ImportRow[];
};

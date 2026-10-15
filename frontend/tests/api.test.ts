import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../src/lib/api";

afterEach(() => vi.unstubAllGlobals());

describe("typed API client", () => {
  it("sends credentials and the CSRF header for writes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await api<{ ok: boolean }>("/api/v1/test", { method: "POST", body: JSON.stringify({ value: 1 }) });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("X-Requested-With")).toBe("FinSight");
  });

  it("surfaces structured API errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Access denied" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    })));
    await expect(api("/api/v1/test")).rejects.toMatchObject<ApiError>({ message: "Access denied", status: 403 });
  });
});

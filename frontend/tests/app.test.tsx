import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "../src/App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("public application entry", () => {
  it("shows the landing page without requiring a session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    })));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);
    expect(await screen.findByRole("heading", { name: /understand your money/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByRole("link", { name: /explore demo/i }).length).toBeGreaterThan(0));
  });
});

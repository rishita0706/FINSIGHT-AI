import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import App from "../src/App";

const user = { id: "user-1", email: "person@example.com" };

function response(data: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockApi(handler: (url: string, init: RequestInit) => Response) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit = {}) =>
    Promise.resolve(handler(String(input), init)),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderApp(path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("application routes and pages", () => {
  it("shows the public landing page without requiring a session", async () => {
    mockApi(() => response({ detail: "Not authenticated" }, 401));
    renderApp();
    expect(await screen.findByRole("heading", { name: /understand your money/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /explore demo/i }).length).toBeGreaterThan(0);
  });

  it("redirects protected routes to sign-in for signed-out users", async () => {
    mockApi(() => response({ detail: "Not authenticated" }, 401));
    renderApp("/app/budgets");
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
  });

  it("signs in a user and opens the protected workspace", async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.endsWith("/auth/me")) return response({ detail: "Not authenticated" }, 401);
      if (url.endsWith("/auth/login") && init.method === "POST") return response(user);
      if (url.endsWith("/analytics/overview")) return response({ income: "0", expenses: "0", net_cash_flow: "0", savings_rate: null, transaction_count: 0, by_category: {} });
      if (url.endsWith("/analytics/cash-flow")) return response([]);
      if (url.endsWith("/analytics/categories")) return response([]);
      if (url.includes("/transactions")) return response({ total: 0, items: [] });
      return response([]);
    });
    const userActions = userEvent.setup();
    renderApp("/auth");
    await userActions.type(await screen.findByLabelText(/email address/i), user.email);
    await userActions.type(screen.getByLabelText("Password"), "correct-password");
    await userActions.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: /your financial overview/i })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/auth/login"), expect.objectContaining({ method: "POST" }));
  });

  it("shows a useful empty dashboard for a signed-in user without transactions", async () => {
    mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/analytics/overview")) return response({
        income: "0", expenses: "0", net_cash_flow: "0", savings_rate: null, transaction_count: 0, by_category: {},
      });
      if (url.endsWith("/analytics/cash-flow")) return response([]);
      if (url.includes("/transactions")) return response({ total: 0, items: [] });
      if (url.endsWith("/analytics/categories")) return response([]);
      return response([]);
    });
    renderApp("/app");
    expect(await screen.findByRole("heading", { name: /your financial overview/i })).toBeInTheDocument();
    expect(await screen.findByText("A fresh start")).toBeInTheDocument();
    expect(screen.getByText("Nothing to break down yet")).toBeInTheDocument();
  });

  it("presents API failures as an inline error instead of a blank dashboard", async () => {
    mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/analytics/overview")) return response({ detail: "Analytics service unavailable" }, 503);
      if (url.endsWith("/analytics/cash-flow")) return response([]);
      return response([]);
    });
    renderApp("/app");
    expect(await screen.findByText("Analytics service unavailable")).toBeInTheDocument();
  });

  it("uploads a statement, reviews extracted rows, then confirms the import", async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/imports") && init.method === "POST") return response({
        id: "import-1", status: "preview", source_type: "csv", warnings: [],
        rows: [{ line: 2, status: "ok", errors: [], date: "2026-09-01", description: "Market", amount: "35.00", direction: "debit", category: "Groceries", tx_type: "expense" }],
      });
      if (url.endsWith("/preview") && init.method === "PATCH") return response({ ok: true });
      if (url.endsWith("/confirm")) return response({ imported: 1 });
      return response([]);
    });
    const userActions = userEvent.setup();
    const { container } = renderApp("/app/import/wizard");
    expect(await screen.findByText("Drop your statement here")).toBeInTheDocument();
    const input = container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input).not.toBeNull();
    fireEvent.change(input!, { target: { files: [new File(["date,description,amount"], "statement.csv", { type: "text/csv" })] } });
    await userActions.click(await screen.findByRole("button", { name: /review statement/i }));
    expect(await screen.findByRole("heading", { name: /1 transactions found/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Description on row 2" })).toHaveValue("Market");
    await userActions.click(screen.getByRole("button", { name: /confirm and import/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/imports/import-1/confirm"),
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByRole("heading", { name: /bring your transactions into focus/i })).toBeInTheDocument();
  });

  it("opens and closes the responsive navigation when a destination is selected", async () => {
    mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.includes("/analytics/categories")) return response([]);
      if (url.includes("/transactions")) return response({ total: 0, items: [] });
      return response([]);
    });
    const userActions = userEvent.setup();
    renderApp("/app");
    const openButton = await screen.findByRole("button", { name: "Open navigation" });
    await userActions.click(openButton);
    expect(screen.getByRole("button", { name: "Close navigation" })).toBeInTheDocument();
    await userActions.click(screen.getByRole("link", { name: "Transactions" }));
    expect(await screen.findByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Close navigation" })).not.toBeInTheDocument();
  });

  it("surfaces low-confidence transaction categorization for review and applies date filters", async () => {
    const fetchMock = mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/analytics/categories")) return response([{ category: "Food", amount: "35" }]);
      if (url.includes("/transactions?")) return response({
        total: 1,
        items: [{ id: "t1", date: "2026-09-01", description: "Market", amount: "35", currency: "INR", direction: "debit", tx_type: "expense", category: "Food", category_source: "rule", category_confidence: "0.42" }],
      });
      return response([]);
    });
    const userActions = userEvent.setup();
    renderApp("/app/transactions");
    expect(await screen.findByText("Needs review")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /transactions/i })).toBeInTheDocument();
    await userActions.type(screen.getByLabelText("Start date"), "2026-09-01");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("start=2026-09-01"), expect.anything()));
  });

  it("shows evaluation metrics, a confusion matrix, and a synthetic-data caveat", async () => {
    mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/ml/categorizer/evaluation")) return response({
        available: true, version: "categorizer-v1", labels: ["Food", "Travel"],
        per_class: { Food: { precision: 0.8, recall: 0.75, support: 4 }, Travel: { precision: 1, recall: 0.5, support: 2 } },
        confusion_matrix: [[3, 1], [1, 1]], needs_review_confidence_threshold: 0.6,
        limitations: "Synthetic examples do not establish real-world accuracy.",
      });
      return response([]);
    });
    renderApp("/app/model-evaluation");
    expect(await screen.findByRole("heading", { name: "Categorizer evaluation" })).toBeInTheDocument();
    expect(await screen.findByText("80.0%")).toBeInTheDocument();
    expect(await screen.findByText(/60%/)).toBeInTheDocument();
    expect(await screen.findByText(/synthetic examples do not establish real-world accuracy/i)).toBeInTheDocument();
    const matrix = screen.getByRole("table", { name: /confusion matrix/i });
    expect(within(matrix).getByRole("row", { name: "Food 3 1" })).toBeInTheDocument();
  });

  it("renders citations with their source link in assistant answers", async () => {
    mockApi((url, init) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/conversations") && init.method === "POST") return response({
        id: "conversation-1", title: "", created_at: "2026-09-01T09:00:00Z", updated_at: "2026-09-01T09:00:00Z",
      }, 201);
      if (url.endsWith("/conversations")) return response([]);
      if (url.endsWith("/conversations/conversation-1")) return response({
        id: "conversation-1", title: "Explain compound interest in simple language.",
        created_at: "2026-09-01T09:00:00Z", updated_at: "2026-09-01T09:00:00Z",
        messages: [
          { id: "user-message", role: "user", content: "Explain compound interest in simple language." },
          {
            id: "assistant-message", role: "assistant", content: "Compound interest grows over time.",
            calculation: null,
            citations: [{ id: "source-1", title: "Interest basics", href: "/api/v1/knowledge/documents/source-1", source_type: "knowledge", reference_url: "https://example.org" }],
            sections: [],
          },
        ],
      });
      if (url.endsWith("/messages")) return response({
        user_message: { id: "user-message", role: "user", content: "Explain compound interest in simple language." },
        assistant_message: {
          id: "assistant-message", role: "assistant", content: "Compound interest grows over time.",
          calculation: null,
          citations: [{ id: "source-1", title: "Interest basics", href: "/api/v1/knowledge/documents/source-1", source_type: "knowledge", reference_url: "https://example.org" }],
          sections: [],
        },
        warnings: [],
      }, 201);
      return response([]);
    });
    const userActions = userEvent.setup();
    renderApp("/app/assistant");
    await userActions.click(await screen.findByRole("button", { name: /explain compound interest/i }));
    const citation = await screen.findByRole("link", { name: /interest basics/i });
    expect(citation).toHaveAttribute("href", "https://example.org");
    expect(citation).toHaveAttribute("target", "_blank");
  });

  it("loads persisted combined sections and deletes a saved conversation", async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/conversations")) return response([{
        id: "conversation-1", title: "Compound interest", created_at: "2026-09-01T09:00:00Z", updated_at: "2026-09-01T09:00:00Z",
      }]);
      if (url.endsWith("/conversations/conversation-1") && init.method === "DELETE") return response(null, 204);
      if (url.endsWith("/conversations/conversation-1")) return response({
        id: "conversation-1",
        title: "Compound interest",
        created_at: "2026-09-01T09:00:00Z",
        updated_at: "2026-09-01T09:00:00Z",
        messages: [
          { id: "u1", role: "user", content: "How much did I spend and what is interest?" },
          {
            id: "a1", role: "assistant", content: "Combined answer.",
            calculation: { metric: "spending", value: "25.00", currency: "INR", definition: "Verified total." },
            citations: [{ id: "source-1", title: "Interest basics", href: "/api/v1/knowledge/documents/source-1", source_type: "knowledge", reference_url: "https://example.org" }],
            sections: [
              { kind: "personal_finance", title: "Your financial data", answer: "You spent ₹25.00.", calculation: { metric: "spending", value: "25.00", currency: "INR", definition: "Verified total." }, citations: [] },
              { kind: "education", title: "General education", answer: "Interest grows over time.", calculation: null, citations: [{ id: "source-1", title: "Interest basics", href: "/api/v1/knowledge/documents/source-1", source_type: "knowledge", reference_url: "https://example.org" }] },
            ],
          },
        ],
      });
      return response([]);
    });
    const userActions = userEvent.setup();
    renderApp("/app/assistant");
    await userActions.click(await screen.findByRole("button", { name: "Compound interest" }));
    expect(await screen.findByText("Your financial data")).toBeInTheDocument();
    expect(screen.getByText("General education")).toBeInTheDocument();
    expect(screen.getByText("Verified total.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /interest basics/i })).toHaveAttribute("href", "https://example.org");
    await userActions.click(screen.getByRole("button", { name: "Delete conversation: Compound interest" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/conversations/conversation-1"),
      expect.objectContaining({ method: "DELETE" }),
    ));
  });

  it("exposes import history and dedicated budget routes", async () => {
    mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/imports")) return response([{ id: "i1", filename: "bank.csv", status: "confirmed", source_type: "csv", created_at: "2026-09-01T09:00:00Z" }]);
      if (url.endsWith("/budgets")) return response([]);
      return response([]);
    });
    renderApp("/app/import/history");
    expect(await screen.findByText("bank.csv")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /import a statement/i })).toHaveAttribute("href", "/app/import/wizard");
    cleanup();
    mockApi((url) => {
      if (url.endsWith("/auth/me")) return response(user);
      if (url.endsWith("/budgets")) return response([]);
      return response([]);
    });
    renderApp("/app/budgets");
    expect(await screen.findByRole("heading", { name: "Budgets" })).toBeInTheDocument();
    expect(await screen.findByText("No budgets yet")).toBeInTheDocument();
  });
});

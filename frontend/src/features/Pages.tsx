import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ArrowDownLeft, ArrowRight, ArrowUpRight, BookOpen, Bot, CalendarDays, Check, CircleHelp, CreditCard, FileUp, LoaderCircle, LogOut, Pencil, Plus, Search, ShieldCheck, Sparkles, Target, TrendingUp, Trash2, Wallet, X } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type ImportPreview, type Overview, type Transaction } from "../lib/api";
import { EmptyState, ErrorState, Loading, Metric, PageHeading } from "../components/ui";
import { toast } from "sonner";

let displayTimezone = "Asia/Kolkata";
const formatMoney = (value: string | number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
const prettyDate = (value: string) =>
  new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: displayTimezone }).format(new Date(`${value}T12:00:00Z`));

export function Dashboard() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: () => api<Overview>("/api/v1/analytics/overview") });
  const cash = useQuery({ queryKey: ["cash-flow"], queryFn: () => api<{ month: string; income: string; expenses: string; net: string }[]>("/api/v1/analytics/cash-flow") });
  const transactions = useQuery({ queryKey: ["transactions", "recent"], queryFn: () => api<{ total: number; items: Transaction[] }>("/api/v1/transactions?page_size=6") });
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<{ category: string; amount: string }[]>("/api/v1/analytics/categories") });
  if (overview.isLoading || cash.isLoading) return <Loading />;
  if (overview.isError) return <ErrorState message={overview.error.message} />;
  const data = overview.data!;
  const categoryRows = categories.data ?? [];
  const palette = ["#2c8c82", "#82b9ac", "#e4b46c", "#8e9dad", "#c8d9d4", "#ba807a"];
  return <>
    <PageHeading eyebrow={new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date()).toUpperCase()} title="Your financial overview" description="A clear look at the money moving through your life." action={<Link className="button button-outline" to="/app/import/wizard"><Plus size={16} /> Add transactions</Link>} />
    <div className="metric-grid">
      <Metric icon={<ArrowDownLeft size={17} />} label="Income recorded" value={formatMoney(data.income)} helper="Credits, excluding transfers" tone="green" />
      <Metric icon={<ArrowUpRight size={17} />} label="Expenses recorded" value={formatMoney(data.expenses)} helper="Debits, excluding transfers" tone="blue" />
      <Metric icon={<Wallet size={17} />} label="Net cash flow" value={formatMoney(data.net_cash_flow)} helper="Income less expenses" tone="sand" />
      <Metric icon={<CreditCard size={17} />} label="Transactions" value={String(data.transaction_count)} helper="Across your recorded history" tone="lilac" />
    </div>
    <div className="dashboard-grid">
      <section className="card chart-card"><div className="card-heading"><div><span className="eyebrow">CASH FLOW</span><h2>Monthly activity</h2></div><span className="subtle-label"><span className="legend-dot teal" /> Income <span className="legend-dot pale" /> Expenses</span></div>
        {cash.isError ? <ErrorState message={cash.error.message} /> : cash.data?.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height={250}><AreaChart data={cash.data} margin={{ top: 16, right: 12, left: -16, bottom: 0 }}><defs><linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2c8c82" stopOpacity={0.2} /><stop offset="95%" stopColor="#2c8c82" stopOpacity={0} /></linearGradient><linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b9cbd0" stopOpacity={0.22} /><stop offset="95%" stopColor="#b9cbd0" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf0f1" /><XAxis dataKey="month" tickFormatter={(v: string) => new Date(`${v}-01`).toLocaleDateString("en-IN", { month: "short" })} axisLine={false} tickLine={false} tick={{ fill: "#93a0ab", fontSize: 12 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#93a0ab", fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `₹${Math.round(v / 1000)}k` : `₹${v}`} /><Tooltip formatter={(v) => formatMoney(String(v))} contentStyle={{ borderRadius: 12, borderColor: "#e8edee" }} /><Area type="monotone" dataKey="income" stroke="#2c8c82" strokeWidth={2.5} fill="url(#incomeFill)" /><Area type="monotone" dataKey="expenses" stroke="#9caeb7" strokeWidth={2} fill="url(#expenseFill)" /></AreaChart></ResponsiveContainer></div> : <EmptyState icon={<TrendingUp />} title="Your trends will show here" text="Import a statement or add transactions to see monthly cash flow." />}</section>
      <section className="card category-card"><div className="card-heading"><div><span className="eyebrow">SPENDING MIX</span><h2>By category</h2></div><Link to="/app/transactions" className="small-link">Details <ArrowRight size={14} /></Link></div>
        {categoryRows.length ? <><div className="donut-wrap"><ResponsiveContainer width="100%" height={170}><PieChart><Pie data={categoryRows.slice(0, 6)} dataKey="amount" nameKey="category" innerRadius={53} outerRadius={76} paddingAngle={3} stroke="none">{categoryRows.slice(0, 6).map((_, index) => <Cell key={index} fill={palette[index % palette.length]} />)}</Pie><Tooltip formatter={(v) => formatMoney(String(v))} /></PieChart></ResponsiveContainer><div className="donut-center"><b>{categoryRows.length}</b><span>categories</span></div></div><div className="category-list">{categoryRows.slice(0, 5).map((item, index) => <div key={item.category}><span className="legend-dot" style={{ background: palette[index % palette.length] }} /><span>{item.category}</span><b>{formatMoney(item.amount)}</b></div>)}</div></> : <EmptyState icon={<Wallet />} title="Nothing to break down yet" text="Your categories appear after you add some transactions." />}</section>
    </div>
    <section className="card recent-card"><div className="card-heading"><div><span className="eyebrow">RECENT ACTIVITY</span><h2>Latest transactions</h2></div><Link to="/app/transactions" className="small-link">All transactions <ArrowRight size={14} /></Link></div>
      {transactions.isError ? <ErrorState message={transactions.error.message} /> : transactions.data?.items.length ? <TransactionTable rows={transactions.data.items} /> : <EmptyState icon={<CalendarDays />} title="A fresh start" text="No transactions yet. Import a bank statement or add one manually." action={<Link className="button button-outline" to="/app/import/wizard">Import statement <ArrowRight size={15} /></Link>} />}
    </section>
    <div className="dashboard-note"><ShieldCheck size={16} /><span>These totals reflect transactions you’ve entered or imported. FinSight doesn’t connect to your bank.</span></div>
  </>;
}

export function TransactionTable({ rows, onEdit, onDelete }: { rows: Transaction[]; onEdit?: (row: Transaction) => void; onDelete?: (row: Transaction) => void }) {
  const evaluation = useQuery({ queryKey: ["categorizer-evaluation"], queryFn: () => api<{ needs_review_confidence_threshold?: number }>("/api/v1/ml/categorizer/evaluation") });
  const reviewThreshold = evaluation.data?.needs_review_confidence_threshold ?? 0.6;
  const [sort, setSort] = useState<{ field: "date" | "description" | "category" | "amount"; direction: "asc" | "desc" }>({ field: "date", direction: "desc" });
  const sortedRows = [...rows].sort((a, b) => {
    const left = sort.field === "amount" ? Number(a.amount) : a[sort.field];
    const right = sort.field === "amount" ? Number(b.amount) : b[sort.field];
    const result = typeof left === "number" && typeof right === "number" ? left - right : String(left).localeCompare(String(right));
    return sort.direction === "asc" ? result : -result;
  });
  function sortBy(field: typeof sort.field) {
    setSort((current) => ({ field, direction: current.field === field && current.direction === "asc" ? "desc" : "asc" }));
  }
  const heading = (field: typeof sort.field, label: string) => <th aria-sort={sort.field === field ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}><button className="table-sort" onClick={() => sortBy(field)}>{label}{sort.field === field ? (sort.direction === "asc" ? " ↑" : " ↓") : ""}</button></th>;
  return <div className="table-scroll"><table className="transaction-table"><caption className="visually-hidden">Transactions. Activate a column heading to change the sort order.</caption><thead><tr>{heading("description", "TRANSACTION")}{heading("date", "DATE")}{heading("category", "CATEGORY")}<th className="align-right" aria-sort={sort.field === "amount" ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}><button className="table-sort" onClick={() => sortBy("amount")}>AMOUNT{sort.field === "amount" ? (sort.direction === "asc" ? " ↑" : " ↓") : ""}</button></th>{onEdit && <th scope="col">MANAGE</th>}</tr></thead><tbody>{sortedRows.map((row) => <tr key={row.id}><td><span className={`tx-icon ${row.direction === "credit" ? "credit" : ""}`}>{row.direction === "credit" ? <ArrowDownLeft size={15} /> : <ArrowUpRight size={15} />}</span><span className="tx-title">{row.description}<small>{row.tx_type === "transfer" ? "Transfer" : row.direction === "credit" ? "Money in" : "Money out"}</small></span></td><td>{prettyDate(row.date)}</td><td><span className="category-tag">{row.category}</span>{row.category_confidence !== null && row.category_confidence !== undefined && Number(row.category_confidence) < reviewThreshold && <span className="review-needed" title={`Categorization confidence ${Math.round(Number(row.category_confidence) * 100)}%`}>Needs review</span>}</td><td className={`align-right amount ${row.direction === "credit" ? "amount-credit" : ""}`}>{row.direction === "credit" ? "+" : "−"}{formatMoney(row.amount)}</td>{onEdit && <td><div className="row-actions"><button aria-label={`Edit ${row.description}`} onClick={() => onEdit(row)}><Pencil size={14} /></button><button aria-label={`Delete ${row.description}`} onClick={() => onDelete?.(row)}><Trash2 size={14} /></button></div></td>}</tr>)}</tbody></table></div>;
}

export function Transactions() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [deleting, setDeleting] = useState<Transaction | null>(null);
  const [page, setPage] = useState(1);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [category, setCategory] = useState("");
  const client = useQueryClient();
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<{ category: string; amount: string }[]>("/api/v1/analytics/categories") });
  const result = useQuery({ queryKey: ["transactions", query, start, end, category, page], queryFn: () => {
    const params = new URLSearchParams({ q: query, page: String(page), page_size: "20" });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    if (category) params.set("category", category);
    return api<{ total: number; items: Transaction[] }>(`/api/v1/transactions?${params}`);
  } });
  const create = useMutation({ mutationFn: (body: object) => api<Transaction>("/api/v1/transactions", { method: "POST", body: JSON.stringify(body) }), onSuccess: () => { client.invalidateQueries({ queryKey: ["transactions"] }); client.invalidateQueries({ queryKey: ["overview"] }); setOpen(false); toast.success("Transaction added"); } });
  const update = useMutation({ mutationFn: (body: object) => api<Transaction>(`/api/v1/transactions/${editing!.id}`, { method: "PATCH", body: JSON.stringify(body) }), onSuccess: () => { client.invalidateQueries(); setOpen(false); setEditing(null); toast.success("Transaction updated"); }, onError: (error: Error) => toast.error(error.message) });
  const remove = useMutation({ mutationFn: (id: string) => api<void>(`/api/v1/transactions/${id}`, { method: "DELETE" }), onSuccess: () => { client.invalidateQueries(); toast.success("Transaction deleted"); }, onError: (error: Error) => toast.error(error.message) });
  return <><PageHeading eyebrow="YOUR RECORDS" title="Transactions" description="Review, search and manage your recorded activity." action={<button className="button button-teal" onClick={() => setOpen(true)}><Plus size={16} /> Add transaction</button>} />
    <section className="card transactions-page"><div className="filter-row"><label className="search-field"><Search size={16} /><input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Search descriptions" /></label><label className="date-filter">From<input aria-label="Start date" type="date" value={start} onChange={(e) => { setStart(e.target.value); setPage(1); }} /></label><label className="date-filter">To<input aria-label="End date" type="date" value={end} onChange={(e) => { setEnd(e.target.value); setPage(1); }} /></label><select aria-label="Filter by category" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}><option value="">All categories</option>{categories.data?.map((item) => <option key={item.category} value={item.category}>{item.category}</option>)}</select><a href={`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1/transactions/export`} className="button button-outline">Export CSV</a></div>
      {result.isLoading ? <Loading /> : result.isError ? <ErrorState message={result.error.message} /> : result.data?.items.length ? <><TransactionTable rows={result.data.items} onEdit={(row) => { setEditing(row); setOpen(true); }} onDelete={setDeleting} /><div className="pagination"><span>{result.data.total} transactions</span><div><button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button disabled={page * 20 >= result.data.total} onClick={() => setPage(page + 1)}>Next</button></div></div></> : <EmptyState icon={<CreditCard />} title={query || start || end || category ? "No matching transactions" : "No transactions yet"} text={query || start || end || category ? "Try adjusting your search or filters." : "Add a transaction manually or import a statement."} />}
    </section>
    {deleting && <ConfirmDialog title="Delete transaction?" message={`“${deleting.description}” will be permanently removed from your transaction history.`} confirmLabel="Delete transaction" onCancel={() => setDeleting(null)} onConfirm={() => { remove.mutate(deleting.id); setDeleting(null); }} />}
    {open && <Modal title={editing ? "Edit transaction" : "Add transaction"} close={() => { setOpen(false); setEditing(null); }}><TransactionForm initial={editing ?? undefined} onSubmit={(values) => editing ? update.mutate(values) : create.mutate(values)} busy={editing ? update.isPending : create.isPending} error={editing ? update.error?.message : create.error?.message} /></Modal>}
  </>;
}
const txSchema = z.object({ date: z.string().min(1), description: z.string().min(1).max(300), amount: z.string().regex(/^\d+(\.\d{1,2})?$/, "Enter a positive amount"), direction: z.enum(["debit", "credit"]), category: z.string().optional() });
export function TransactionForm({ initial, onSubmit, busy, error }: { initial?: Partial<Transaction>; onSubmit: (v: z.infer<typeof txSchema>) => void; busy: boolean; error?: string }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof txSchema>>({ resolver: zodResolver(txSchema), defaultValues: { date: initial?.date ?? new Date().toISOString().slice(0, 10), description: initial?.description ?? "", amount: initial?.amount ?? "", direction: initial?.direction ?? "debit", category: initial?.category ?? "" } });
  return <form className="modal-form" onSubmit={handleSubmit(onSubmit)}><label>Date<input type="date" {...register("date")} /></label><label>Description<input placeholder="e.g. Grocery shopping" {...register("description")} />{errors.description && <small className="field-error">{errors.description.message}</small>}</label><div className="form-row"><label>Amount (₹)<input inputMode="decimal" placeholder="0.00" {...register("amount")} />{errors.amount && <small className="field-error">{errors.amount.message}</small>}</label><label>Direction<select {...register("direction")}><option value="debit">Expense</option><option value="credit">Income / credit</option></select></label></div><label>Category<input placeholder="Auto-categorized if empty" {...register("category")} /></label>{error && <div className="form-error">{error}</div>}<button className="button button-dark full-button" disabled={busy}>{busy ? "Saving…" : initial ? "Save changes" : "Save transaction"} <ArrowRight size={15} /></button></form>;
}
export function Modal({ title, close, children }: { title: string; close: () => void; children: ReactNode }) {
  useEffect(() => { const listener = (event: KeyboardEvent) => event.key === "Escape" && close(); window.addEventListener("keydown", listener); return () => window.removeEventListener("keydown", listener); }, [close]);
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && close()}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-heading"><h2 id="modal-title">{title}</h2><button className="icon-button" onClick={close} aria-label="Close"><X size={18} /></button></div>{children}</section></div>;
}

export function ConfirmDialog({ title, message, confirmLabel, onCancel, onConfirm }: { title: string; message: string; confirmLabel: string; onCancel: () => void; onConfirm: () => void }) {
  return <Modal title={title} close={onCancel}><p className="confirm-message">{message}</p><div className="confirm-actions"><button className="button button-outline" onClick={onCancel}>Cancel</button><button className="button button-danger" onClick={onConfirm}>{confirmLabel}</button></div></Modal>;
}

type Budget = { id: string; category: string; amount: string; period_start: string; spent: string; usage: string };
type ImportRecord = { id: string; filename: string; status: string; source_type: string; created_at: string };

export function Budgets() {
  const client = useQueryClient();
  const budgets = useQuery({ queryKey: ["budgets"], queryFn: () => api<Budget[]>("/api/v1/budgets") });
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7) + "-01");
  const create = useMutation({
    mutationFn: () => api<Budget>("/api/v1/budgets", { method: "POST", body: JSON.stringify({ category, amount, period_start: period }) }),
    onSuccess: () => { setCategory(""); setAmount(""); client.invalidateQueries({ queryKey: ["budgets"] }); toast.success("Budget created"); },
    onError: (error: Error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/budgets/${id}`, { method: "DELETE" }),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["budgets"] }); toast.success("Budget removed"); },
    onError: (error: Error) => toast.error(error.message),
  });
  return <><PageHeading eyebrow="SPENDING PLAN" title="Budgets" description="Set a monthly guide by category and keep an eye on recorded spending." action={<Link className="button button-outline" to="/app/goals"><Target size={15} /> Savings goals</Link>} />
    <section className="card budgets-page"><div className="card-heading"><div><span className="eyebrow">MONTHLY BUDGETS</span><h2>Spending guides</h2></div><Wallet size={19} /></div>
      {budgets.isLoading ? <Loading /> : budgets.isError ? <ErrorState message={budgets.error.message} /> : budgets.data?.length ? <div className="budget-list">{budgets.data.map((budget) => {
        const usage = Math.max(0, Number(budget.usage));
        return <article className="budget-item" key={budget.id}><div className="budget-item-heading"><span className="goal-icon budget"><Wallet size={17} /></span><div><b>{budget.category}</b><small>{new Date(`${budget.period_start}T12:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</small></div><button className="text-danger" onClick={() => remove.mutate(budget.id)}>Remove</button></div>
          <div className="budget-numbers"><span>{formatMoney(budget.spent)} spent</span><b>{formatMoney(budget.amount)} limit</b><strong>{Math.round(usage * 100)}%</strong></div><div className="progress-track"><i className={usage >= 1 ? "over-budget" : ""} style={{ width: `${Math.min(usage * 100, 100)}%` }} /></div>
        </article>;
      })}</div> : <EmptyState icon={<Wallet />} title="No budgets yet" text="Create a category budget to get a clear monthly spending guide." />}
      <form className="budget-form" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
        <h3>Create a monthly budget</h3><label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="e.g. Groceries" required /></label>
        <label>Monthly limit (₹)<input value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" placeholder="0.00" pattern="\\d+(\\.\\d{1,2})?" required /></label>
        <label>Budget month<input type="month" value={period.slice(0, 7)} onChange={(event) => setPeriod(`${event.target.value}-01`)} required /></label>
        <button className="button button-teal" disabled={create.isPending || !category || !amount}>{create.isPending ? "Saving…" : <><Plus size={15} /> Add budget</>}</button>
      </form><p className="muted">Usage sums recorded same-category debits for the budget month; transfers are excluded.</p>
    </section>
  </>;
}

export function ImportHistory() {
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api<ImportRecord[]>("/api/v1/imports") });
  return <><PageHeading eyebrow="YOUR STATEMENT ACTIVITY" title="Import history" description="Review your recent statement imports and their status." action={<Link className="button button-teal" to="/app/import/wizard"><Plus size={15} /> Import a statement</Link>} />
    <section className="card import-history-card">{imports.isLoading ? <Loading /> : imports.isError ? <ErrorState message={imports.error.message} /> : imports.data?.length ? <div className="table-scroll"><table className="transaction-table"><thead><tr><th>FILE</th><th>TYPE</th><th>IMPORTED</th><th>STATUS</th></tr></thead><tbody>{imports.data.map((item) => <tr key={item.id}><td className="import-filename">{item.filename}</td><td>{item.source_type.toUpperCase()}</td><td>{new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}</td><td><span className={`status-tag ${item.status}`}>{item.status.replaceAll("_", " ")}</span></td></tr>)}</tbody></table></div> : <EmptyState icon={<FileUp />} title="No imports yet" text="Your completed statement imports will appear here." action={<Link className="button button-outline" to="/app/import/wizard">Start an import <ArrowRight size={15} /></Link>} />}</section>
  </>;
}

type CategorizerEvaluation = {
  available: boolean;
  message?: string;
  version?: string;
  per_class?: Record<string, { precision: number; recall: number; support: number }>;
  confusion_matrix?: number[][];
  labels?: string[];
  needs_review_confidence_threshold?: number;
  needs_review_policy?: string;
  limitations?: string;
};

export function ModelEvaluation() {
  const evaluation = useQuery({ queryKey: ["categorizer-evaluation"], queryFn: () => api<CategorizerEvaluation>("/api/v1/ml/categorizer/evaluation") });
  return <><PageHeading eyebrow="MODEL TRANSPARENCY" title="Categorizer evaluation" description="Evaluation metrics for the optional transaction categorizer." />
    <section className="card evaluation-card">{evaluation.isLoading ? <Loading /> : evaluation.isError ? <ErrorState message={evaluation.error.message} /> : !evaluation.data?.available ? <EmptyState icon={<CircleHelp />} title="Evaluation not available" text={evaluation.data?.message ?? "The evaluation report has not been generated."} /> : <>
      <div className="evaluation-heading"><div><span className="eyebrow">EVALUATION REPORT</span><h2>{evaluation.data.version ?? "Categorizer"}</h2></div><span className="status-tag ok">Evaluation available</span></div>
      <p className="evaluation-policy">{evaluation.data.needs_review_policy ?? "Low-confidence predictions should be reviewed."} Threshold: <b>{Math.round((evaluation.data.needs_review_confidence_threshold ?? 0.6) * 100)}%</b>.</p>
      <div className="evaluation-layout"><section><h3>Per-class performance</h3><div className="table-scroll"><table className="transaction-table evaluation-table"><caption className="visually-hidden">Categorizer precision, recall, and evaluation support by class</caption><thead><tr><th scope="col">CLASS</th><th scope="col">PRECISION</th><th scope="col">RECALL</th><th scope="col">SUPPORT</th></tr></thead><tbody>{Object.entries(evaluation.data.per_class ?? {}).map(([label, metrics]) => <tr key={label}><th scope="row">{label}</th><td>{(metrics.precision * 100).toFixed(1)}%</td><td>{(metrics.recall * 100).toFixed(1)}%</td><td>{metrics.support}</td></tr>)}</tbody></table></div></section>
        <section><h3>Confusion matrix</h3><p className="muted">Rows are actual classes; columns are predicted classes.</p><div className="table-scroll matrix-scroll"><table className="transaction-table matrix-table"><caption className="visually-hidden">Confusion matrix with actual classes on rows and predicted classes on columns</caption><thead><tr><th scope="col">ACTUAL / PREDICTED</th>{(evaluation.data.labels ?? []).map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{(evaluation.data.confusion_matrix ?? []).map((row, rowIndex) => <tr key={evaluation.data?.labels?.[rowIndex] ?? rowIndex}><th scope="row">{evaluation.data?.labels?.[rowIndex] ?? `Class ${rowIndex + 1}`}</th>{row.map((count, columnIndex) => <td key={evaluation.data?.labels?.[columnIndex] ?? columnIndex}>{count}</td>)}</tr>)}</tbody></table></div></section>
      </div><div className="synthetic-caveat"><ShieldCheck size={18} /><p><b>Important limitation</b><br />{evaluation.data.limitations ?? "These metrics are based on synthetic data and do not demonstrate real-world accuracy."} Results should not be interpreted as a guarantee for your transactions.</p></div>
    </>}</section>
  </>;
}

export function ImportWizard() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [password, setPassword] = useState("");
  const [dragging, setDragging] = useState(false);
  const client = useQueryClient();
  const upload = useMutation({ mutationFn: async () => { if (!file) throw new Error("Choose a file first"); const form = new FormData(); form.append("file", file); if (password) form.append("password", password); return api<ImportPreview>("/api/v1/imports", { method: "POST", body: form }); }, onSuccess: setPreview, onError: (error: Error) => toast.error(error.message) });
  const confirm = useMutation({ mutationFn: async () => { const corrections = preview!.rows.filter((row) => row.status === "ok" || row.status === "error").map(({ line, date, description, amount, direction, category, tx_type }) => ({ line, date, description, amount, direction, category, tx_type })); if (corrections.length) await api(`/api/v1/imports/${preview!.id}/preview`, { method: "PATCH", body: JSON.stringify({ rows: corrections }) }); return api<{ imported: number }>(`/api/v1/imports/${preview!.id}/confirm`, { method: "POST" }); }, onSuccess: (result) => { toast.success(`${result.imported} transactions imported`); setPreview(null); setFile(null); setPassword(""); client.invalidateQueries(); }, onError: (error: Error) => toast.error(error.message) });
  function choose(next: File | undefined) { if (!next) return; if (!/\.(pdf|csv)$/i.test(next.name)) { toast.error("Choose a PDF or CSV file"); return; } setFile(next); setPreview(null); }
  return <><PageHeading eyebrow="SECURE IMPORT" title="Bring your transactions into focus" description="Upload a statement, review every row, then choose what to save." />
    {!preview ? <section className="card import-card"><div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }}><input id="statement-file" type="file" accept=".pdf,.csv,application/pdf,text/csv" onChange={(event) => choose(event.target.files?.[0])} /><label htmlFor="statement-file"><span className="upload-icon"><FileUp size={23} /></span><b>{file ? file.name : "Drop your statement here"}</b><span>{file ? `${(file.size / 1024).toFixed(0)} KB · Ready to review` : "or browse from your device"}</span><small>PDF or CSV · up to 2 MB</small></label></div>
      {file?.name.toLowerCase().endsWith(".pdf") && <label className="password-label">PDF password, if required <input type="password" autoComplete="off" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Only used for this import; never stored" /></label>}
      <div className="import-actions"><div><ShieldCheck size={17} /><span>Files are processed temporarily and are not kept as statement archives.</span></div><button disabled={!file || upload.isPending} className="button button-teal" onClick={() => upload.mutate()}>{upload.isPending ? <LoaderCircle className="spin" size={16} /> : <FileUp size={16} />} Review statement</button></div>
      {upload.isError && <div className="form-error import-error">{upload.error.message}</div>}</section> :
      <section className="card review-card"><div className="review-summary"><div><span className="eyebrow">REVIEW BEFORE SAVING</span><h2>{preview.rows.filter((row) => row.status === "ok").length} transactions found</h2><p>{preview.source_type.toUpperCase()} · {preview.warnings?.join(" ") || "Review extracted data before saving."}</p></div><button className="button button-outline" onClick={() => setPreview(null)}>Choose another file</button></div><div className="review-warning"><ShieldCheck size={17} /> Extraction can be imperfect. Correct amounts, dates and direction before confirming.</div><div className="table-scroll"><table className="transaction-table review-table"><thead><tr><th>DATE</th><th>DESCRIPTION</th><th>DIRECTION</th><th>AMOUNT</th><th>STATUS</th></tr></thead><tbody>{preview.rows.map((row, index) => <tr key={`${row.line}-${index}`}><td><input className="review-input" aria-label={`Date on row ${row.line}`} type="date" value={row.date ?? ""} onChange={(event) => setPreview({ ...preview, rows: preview.rows.map((item, rowIndex) => rowIndex === index ? { ...item, date: event.target.value } : item) })} /></td><td><input className="review-input review-description" aria-label={`Description on row ${row.line}`} value={row.description ?? ""} placeholder={row.errors.join(", ")} onChange={(event) => setPreview({ ...preview, rows: preview.rows.map((item, rowIndex) => rowIndex === index ? { ...item, description: event.target.value } : item) })} /></td><td><select className="review-input" aria-label={`Direction on row ${row.line}`} value={row.direction ?? ""} onChange={(event) => setPreview({ ...preview, rows: preview.rows.map((item, rowIndex) => rowIndex === index ? { ...item, direction: event.target.value as "debit" | "credit" } : item) })}><option value="" disabled>Select</option><option value="debit">Debit</option><option value="credit">Credit</option></select></td><td><input className="review-input" aria-label={`Amount on row ${row.line}`} inputMode="decimal" value={row.amount ?? ""} onChange={(event) => setPreview({ ...preview, rows: preview.rows.map((item, rowIndex) => rowIndex === index ? { ...item, amount: event.target.value } : item) })} /></td><td><span className={`status-tag ${row.status}`}>{row.status === "error" && row.date && row.description && row.amount && row.direction ? "ready on confirm" : row.status}</span></td></tr>)}</tbody></table></div><div className="review-footer"><span>{preview.rows.filter((row) => row.status !== "ok").length} skipped or needs correction · No data is saved until you confirm</span><button disabled={!preview.rows.some((row) => row.status === "ok" || (row.status === "error" && row.date && row.description && row.amount && row.direction)) || confirm.isPending} className="button button-teal" onClick={() => confirm.mutate()}>{confirm.isPending ? "Saving…" : <><Check size={16} /> Confirm and import</>}</button></div>{confirm.isError && <div className="form-error">{confirm.error.message}</div>}</section>}
    <div className="import-help-grid"><div><span className="help-icon"><FileUp size={17} /></span><b>Text-based PDF statements</b><p>Generic extraction works best with selectable-text statements. Scanned PDFs and some bank layouts need CSV or manual entry.</p></div><div><span className="help-icon"><ShieldCheck size={17} /></span><b>Your review comes first</b><p>Nothing is written to your transaction history until you confirm. Duplicate rows are detected per account.</p></div></div>
  </>;
}

type AssistantCalculation = {
  metric: string;
  value: string;
  currency: string;
  date_range?: { start: string; end: string };
  definition: string;
  transaction_count?: number;
};
type AssistantCitation = {
  id: string;
  title: string;
  href: string;
  source_type: string;
  reference_url: string;
};
type AssistantSection = {
  kind: string;
  title: string;
  answer: string;
  calculation: AssistantCalculation | null;
  citations: AssistantCitation[];
};
type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  calculation?: AssistantCalculation | null;
  citations?: AssistantCitation[];
  sections?: AssistantSection[];
  created_at?: string;
};
type AssistantConversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: AssistantMessage[];
};
type AssistantMessageResponse = {
  user_message: AssistantMessage;
  assistant_message: AssistantMessage;
  warnings: string[];
};

function CalculationCard({ calculation }: { calculation: AssistantCalculation }) {
  return <div className="calculation-card">
    <div><span>Metric</span><b>{calculation.metric.replaceAll("_", " ")}</b></div>
    <div><span>Value</span><b>{formatMoney(calculation.value)}</b></div>
    {calculation.date_range && <div><span>Date range</span><b>{calculation.date_range.start} — {calculation.date_range.end}</b></div>}
    <small>{calculation.definition}</small>
  </div>;
}

function CitationCards({ citations }: { citations: AssistantCitation[] }) {
  if (!citations.length) return null;
  return <div className="citation-list"><b>Retrieved sources</b>{citations.map((citation) =>
    <a key={citation.id} href={citation.reference_url} target="_blank" rel="noreferrer">
      <BookOpen size={14} /><span>{citation.title}<small>{citation.source_type} · Verified reference</small></span><ArrowRight size={13} />
    </a>
  )}</div>;
}

export function Assistant() {
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<AssistantConversation[]>("/api/v1/conversations"),
  });
  const conversation = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => api<AssistantConversation>(`/api/v1/conversations/${conversationId}`),
    enabled: conversationId !== null,
  });
  const create = useMutation({
    mutationFn: () => api<AssistantConversation>("/api/v1/conversations", { method: "POST" }),
    onSuccess: async (created) => {
      setConversationId(created.id);
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const send = useMutation({
    mutationFn: async (text: string) => {
      const activeId = conversationId ?? (await api<AssistantConversation>("/api/v1/conversations", { method: "POST" })).id;
      const response = await api<AssistantMessageResponse>(`/api/v1/conversations/${activeId}/messages`, {
        method: "POST",
        body: JSON.stringify({ question: text }),
      });
      return { activeId, response };
    },
    onSuccess: async ({ activeId, response }) => {
      setConversationId(activeId);
      setQuestion("");
      if (response.warnings?.length) response.warnings.forEach((warning) => toast.warning(warning));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["conversations"] }),
        queryClient.invalidateQueries({ queryKey: ["conversation", activeId] }),
      ]);
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/conversations/${id}`, { method: "DELETE" }),
    onSuccess: async (_, deletedId) => {
      const remaining = (conversations.data ?? []).filter((item) => item.id !== deletedId);
      queryClient.setQueryData(["conversations"], remaining);
      queryClient.removeQueries({ queryKey: ["conversation", deletedId] });
      setConversationId(remaining[0]?.id ?? null);
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const messages = conversation.data?.messages ?? [];
  const selectedConversation = conversations.data?.find((item) => item.id === conversationId);

  function ask(text: string) {
    if (text.trim()) send.mutate(text.trim());
  }

  function renderAssistantMessage(message: AssistantMessage) {
    const sections = message.sections ?? [];
    return <div className="assistant-response" key={message.id}>
      <span className="assistant-spark"><Sparkles size={15} /></span>
      <div>
        {sections.length ? sections.map((section) => <section className="assistant-section" key={section.kind}>
          <span className="answer-mode">{section.title}</span>
          <p>{section.answer}</p>
          {section.calculation && <CalculationCard calculation={section.calculation} />}
          <CitationCards citations={section.citations} />
        </section>) : <>
          <span className="answer-mode">{message.citations?.length ? "RETRIEVED EDUCATIONAL NOTE" : "VERIFIED ANSWER"}</span>
          <p>{message.content}</p>
          {message.calculation && <CalculationCard calculation={message.calculation} />}
          <CitationCards citations={message.citations ?? []} />
        </>}
      </div>
    </div>;
  }

  return <>
    <PageHeading eyebrow="GROUNDED IN YOUR RECORDS" title="Ask FinSight" description="Get clear calculations from your transaction history, or explore financial topics." action={<button className="button button-teal" onClick={() => create.mutate()} disabled={create.isPending}><Plus size={15} /> New conversation</button>} />
    <div className="assistant-layout">
      <aside className="assistant-history card" aria-label="Conversation history">
        <span className="eyebrow">YOUR CONVERSATIONS</span>
        {conversations.isError && <ErrorState message={conversations.error.message} />}
        {conversations.data?.map((item) => <div className="conversation-list-item" key={item.id}>
          <button className={item.id === conversationId ? "selected" : ""} onClick={() => setConversationId(item.id)} title={item.title || "New conversation"}>
            <span>{item.title || "New conversation"}</span>
          </button>
          <button className="icon-button" aria-label={`Delete conversation: ${item.title || "New conversation"}`} onClick={() => remove.mutate(item.id)} disabled={remove.isPending}><Trash2 size={14} /></button>
        </div>)}
        {!conversations.isLoading && !conversations.data?.length && <p className="muted">Your saved conversations will appear here.</p>}
      </aside>
      <section className="card assistant-card">
        <div className="assistant-messages" aria-live="polite">
          {conversation.isLoading && <Loading />}
          {messages.length ? messages.map((message) => message.role === "user"
            ? <div className="assistant-user-msg" key={message.id}>{message.content}</div>
            : renderAssistantMessage(message)
          ) : !conversation.isLoading && <div className="assistant-welcome">
            <span className="assistant-spark"><Sparkles size={21} /></span><h2>What would you like to understand?</h2>
            <p>Your personal finance answers use your records and deterministic calculations. Educational answers retrieve local notes and show their sources.</p>
            <div className="suggestions">{["How much did I spend this month?", "How much did I spend on food last month?", "Explain compound interest in simple language."].map((text) =>
              <button onClick={() => ask(text)} key={text} disabled={send.isPending}>{text}<ArrowRight size={14} /></button>
            )}</div>
          </div>}
          {send.isPending && <div className="assistant-response"><LoaderCircle className="spin" size={17} /><span>Checking your records…</span></div>}
          {conversation.isError && <ErrorState message={conversation.error.message} />}
        </div>
        <form className="assistant-input" onSubmit={(event: FormEvent) => { event.preventDefault(); ask(question); }}>
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about your transactions or a money topic…" />
          <button className="button button-teal" disabled={!question.trim() || send.isPending}>{send.isPending ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}<span>Ask</span></button>
        </form>
        <p className="assistant-disclaimer">FinSight is informational, not individualized investment, lending or tax advice.</p>
      </section>
      <aside className="assistant-aside">
        {selectedConversation && <div className="card conversation-actions"><span className="eyebrow">SAVED THREAD</span><b>{selectedConversation.title || "New conversation"}</b><button className="button button-outline" onClick={() => remove.mutate(selectedConversation.id)} disabled={remove.isPending}><Trash2 size={14} /> Delete conversation</button></div>}
        <div className="card"><span className="eyebrow">HOW ANSWERS WORK</span><h3>Your data stays the source of truth.</h3><p>Calculations are performed by validated operations on your signed-in account. Educational answers retrieve locally curated notes.</p><div className="aside-divider" /><div className="aside-point"><Check size={15} /> User-scoped transaction records</div><div className="aside-point"><Check size={15} /> Fixed-precision money calculations</div><div className="aside-point"><Check size={15} /> Transfers excluded from spending totals</div><Link className="small-link" to="/app/learn">Explore the knowledge library <ArrowRight size={13} /></Link></div>
        <div className="mock-note"><Bot size={18} /><span><b>Local assistant mode</b><small>Deterministic calculations + lexical retrieval. No LLM API key needed.</small></span></div>
      </aside>
    </div>
  </>;
}

export function Learn() {
  const documents = useQuery({ queryKey: ["knowledge"], queryFn: () => api<{ id: string; title: string; topic: string; source_type: string; reference_url: string; updated_at: string }[]>("/api/v1/knowledge/documents") });
  return <><PageHeading eyebrow="FINANCIAL EDUCATION" title="Learn at your own pace" description="Plain-language notes to help you understand common money topics." /><section className="knowledge-grid">{documents.isLoading ? <Loading /> : documents.isError ? <ErrorState message={documents.error.message} /> : documents.data?.map((document) => <article className="card knowledge-card" key={document.id}><span className="knowledge-icon"><BookOpen size={18} /></span><span className="eyebrow">{document.topic}</span><h2>{document.title}</h2><p>FinSight-authored general education note. Not individualized financial advice.</p><div className="knowledge-meta">Updated {document.updated_at}</div><a href={document.reference_url} target="_blank" rel="noreferrer" className="small-link">RBI financial education <ArrowRight size={13} /></a></article>)}</section><div className="dashboard-note"><ShieldCheck size={16} /><span>Notes are written for general learning. External reference links are provided for further reading and do not imply endorsement of a particular financial product.</span></div></>;
}

export function Insights() {
  const insights = useQuery({ queryKey: ["insights"], queryFn: () => api<{ items: { title: string; detail: string; method: string; type: string }[]; anomaly_candidates: { transaction_id: string; date: string; description: string; amount: string; category: string; reason: string; warning: string }[]; limitations: string[] }>("/api/v1/insights") });
  const forecast = useQuery({ queryKey: ["forecast"], queryFn: () => api<{ available: boolean; message?: string; estimate?: string; method?: string; history_months?: string[]; warning?: string }>("/api/v1/forecasts") });
  return <><PageHeading eyebrow="PATTERNS, NOT CERTAINTY" title="Financial insights" description="Transparent observations based on the records you’ve provided." />{insights.isLoading || forecast.isLoading ? <Loading /> : insights.isError ? <ErrorState message={insights.error.message} /> : <div className="insights-grid"><section className="card goals-card"><span className="eyebrow">RECORDED TRENDS</span><h2>What changed</h2>{insights.data?.items.length ? insights.data.items.map((item) => <article className="insight-item" key={item.type}><span className="insight-icon"><TrendingUp size={17} /></span><div><b>{item.title}</b><p>{item.detail}</p><small>Method: {item.method}</small></div></article>) : <EmptyState icon={<TrendingUp />} title="More history, clearer patterns" text="Record activity across two months to see a spending comparison." />}<div className="aside-divider" /><span className="eyebrow">UNUSUAL TRANSACTION CANDIDATES</span>{insights.data?.anomaly_candidates.length ? insights.data.anomaly_candidates.map((item) => <article className="insight-item" key={item.transaction_id}><span className="insight-icon warning"><CircleHelp size={17} /></span><div><b>{item.description} · {formatMoney(item.amount)}</b><p>{item.reason} {item.warning}</p><small>{prettyDate(item.date)} · {item.category}</small></div></article>) : <p className="muted">No unusual transactions flagged. At least five same-category debits are needed for a baseline.</p>}<p className="muted">{insights.data?.limitations.join(" ")}</p></section><section className="card goals-card forecast-card"><span className="eyebrow">SPENDING BASELINE</span><h2>Month-end forecast</h2>{forecast.isError ? <ErrorState message={forecast.error.message} /> : forecast.data?.available ? <><div className="forecast-value">{formatMoney(forecast.data.estimate ?? "0")}</div><p>{forecast.data.method}</p><div className="forecast-history">{forecast.data.history_months?.map((month) => <span key={month}>{month}</span>)}</div><div className="review-warning">{forecast.data.warning}</div></> : <EmptyState icon={<TrendingUp />} title="Not enough complete history" text={forecast.data?.message ?? "More monthly records are needed."} />}</section></div>}</>;
}

export function Recurring() {
  const client = useQueryClient();
  const recurring = useQuery({ queryKey: ["recurring"], queryFn: () => api<{ merchant: string; typical_amount: string; frequency: string; last_observed: string; confidence: string; status: string; transaction_count: number }[]>("/api/v1/recurring") });
  async function update(merchant: string, action: "confirm" | "dismiss") {
    try {
      await api(`/api/v1/recurring/${encodeURIComponent(merchant)}/${action}`, { method: "POST" });
      await client.invalidateQueries({ queryKey: ["recurring"] });
      toast.success(action === "confirm" ? "Recurring item confirmed" : "Candidate dismissed");
    } catch (error) { toast.error(error instanceof Error ? error.message : "Unable to update recurring item"); }
  }
  return <><PageHeading eyebrow="REPEATING ACTIVITY" title="Recurring payments" description="Heuristic candidates based on repeated descriptions and transaction timing—not confirmed subscriptions." />{recurring.isLoading ? <Loading /> : recurring.isError ? <ErrorState message={recurring.error.message} /> : recurring.data?.length ? <div className="recurring-grid">{recurring.data.map((item) => <article className="card recurring-card" key={item.merchant}><div className="recurring-heading"><span className="goal-icon budget"><CalendarDays size={17} /></span><div><b>{item.merchant}</b><small>{item.frequency} · {item.transaction_count} recorded transactions</small></div><span className={`status-tag ${item.status === "confirmed" ? "ok" : item.status}`}>{item.status}</span></div><div className="recurring-meta"><span>Typical amount<strong>{formatMoney(item.typical_amount)}</strong></span><span>Last observed<strong>{prettyDate(item.last_observed)}</strong></span><span>Confidence<strong>Heuristic only</strong></span></div>{item.status === "candidate" && <div className="settings-actions"><button className="button button-outline" onClick={() => update(item.merchant, "dismiss")}>Dismiss</button><button className="button button-teal" onClick={() => update(item.merchant, "confirm")}><Check size={15} /> Confirm recurring</button></div>}</article>)}</div> : <section className="card"><EmptyState icon={<CalendarDays />} title="No likely recurring items" text="FinSight needs repeated transactions with similar descriptions and intervals before it can suggest a pattern." /></section>}</>;
}

export function Goals() {
  const client = useQueryClient();
  const goals = useQuery({ queryKey: ["goals"], queryFn: () => api<{ id: string; name: string; target_amount: string; saved_amount: string; progress: string; target_date: string | null }[]>("/api/v1/goals") });
  const [goalName, setGoalName] = useState("");
  const [target, setTarget] = useState("");
  const createGoal = useMutation({ mutationFn: () => api("/api/v1/goals", { method: "POST", body: JSON.stringify({ name: goalName, target_amount: target, saved_amount: "0" }) }), onSuccess: () => { setGoalName(""); setTarget(""); client.invalidateQueries({ queryKey: ["goals"] }); toast.success("Goal created"); }, onError: (error: Error) => toast.error(error.message) });
  return <><PageHeading eyebrow="PLAN WITH PURPOSE" title="Savings goals" description="Make a plan for what matters next. Your progress reflects the values you enter." action={<Link className="button button-outline" to="/app/budgets"><Wallet size={15} /> Manage budgets</Link>} /><section className="card goals-card"><div className="card-heading"><div><span className="eyebrow">SAVINGS GOALS</span><h2>What are you working toward?</h2></div><Target size={19} /></div>{goals.isLoading ? <Loading /> : goals.isError ? <ErrorState message={goals.error.message} /> : goals.data?.length ? <div className="goal-list">{goals.data.map((goal) => <div className="goal-item" key={goal.id}><div className="goal-top"><span className="goal-icon"><Target size={17} /></span><div><b>{goal.name}</b><small>{formatMoney(goal.saved_amount)} saved of {formatMoney(goal.target_amount)}</small></div><button className="text-danger" onClick={() => api(`/api/v1/goals/${goal.id}`, { method: "DELETE" }).then(() => client.invalidateQueries({ queryKey: ["goals"] }))}>Remove</button></div><div className="progress-track"><i style={{ width: `${Math.max(0, Math.min(Number(goal.progress) * 100, 100))}%` }} /></div></div>)}</div> : <EmptyState icon={<Target />} title="No goals yet" text="Create a savings goal to give your progress a purpose." />}<form className="inline-create" onSubmit={(e) => { e.preventDefault(); createGoal.mutate(); }}><input value={goalName} onChange={(e) => setGoalName(e.target.value)} placeholder="Goal name" required /><input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Target (₹)" inputMode="decimal" required /><button className="button button-teal" disabled={createGoal.isPending}><Plus size={15} /> Add goal</button></form></section></>;
}

export function SettingsPage({ onSignOut }: { onSignOut: () => Promise<void> }) {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<{ currency: string; timezone: string; bank_connectivity: string; bank_connectivity_message?: string }>("/api/v1/settings") });
  const [timezone, setTimezone] = useState<string | null>(null);
  const timezoneValue = timezone ?? settings.data?.timezone ?? "Asia/Kolkata";
  async function save() { try { await api("/api/v1/settings", { method: "PATCH", body: JSON.stringify({ timezone: timezoneValue }) }); displayTimezone = timezoneValue; await queryClient.invalidateQueries({ queryKey: ["settings"] }); toast.success("Preferences saved"); } catch (error) { toast.error(error instanceof Error ? error.message : "Unable to save"); } }
  async function removeTransactions() { if (!window.confirm("Permanently delete all your transactions? This cannot be undone.")) return; try { await api("/api/v1/settings/transactions", { method: "DELETE" }); await queryClient.invalidateQueries(); toast.success("Transaction history deleted"); } catch (error) { toast.error(error instanceof Error ? error.message : "Unable to delete data"); } }
  async function downloadExport() { try { const data = await api<unknown>("/api/v1/settings/export", { method: "POST" }); const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); link.download = "finsight-export.json"; link.click(); URL.revokeObjectURL(link.href); } catch (error) { toast.error(error instanceof Error ? error.message : "Export failed"); } }
  return <><PageHeading eyebrow="YOUR ACCOUNT" title="Settings & privacy" description="Manage the details that shape your workspace." /><div className="settings-layout"><section className="card settings-card"><span className="eyebrow">PREFERENCES</span><h2>Regional settings</h2><p>Transactions are stored in INR; currency conversion is not applied in this MVP.</p>{settings.isError ? <ErrorState message={settings.error.message} /> : <><label>Currency<input value="Indian Rupee (₹ INR)" readOnly /></label><label>Timezone<input value={timezoneValue} onChange={(e) => setTimezone(e.target.value)} /></label><button className="button button-teal" onClick={save}>Save preferences <Check size={15} /></button></>}</section><section className="card settings-card"><span className="eyebrow">DATA & PRIVACY</span><h2>You’re in control</h2><p>Download a copy of your data or remove transaction history from your account.</p><div className="settings-callout"><ShieldCheck size={19} /><span><b>{settings.data?.bank_connectivity_message ?? "Live bank connections are not available."}</b><small>FinSight will never ask for your bank password, OTP or UPI PIN.</small></span></div><div className="settings-actions"><button className="button button-outline" onClick={downloadExport}>Export my data</button><button className="button button-danger-outline" onClick={removeTransactions}>Delete transactions</button></div><div className="settings-actions"><button className="button button-outline" onClick={onSignOut}><LogOut size={15} /> Sign out</button><button className="button button-danger-outline" onClick={async () => { if (!window.confirm("Delete your account and associated data permanently?")) return; await api("/api/v1/settings/account", { method: "DELETE" }); onSignOut(); }}>Delete account</button></div></section></div></>;
}

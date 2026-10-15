import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  ArrowDownLeft, ArrowRight, ArrowUpRight, BookOpen, Bot, CalendarDays, Check, ChevronDown, CircleHelp,
  CreditCard, FileUp, LayoutDashboard, LoaderCircle, LogOut, Menu, Pencil, Plus, Search,
  Settings, ShieldCheck, Sparkles, Target, TrendingUp, Trash2, Wallet, X,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type ImportPreview, type Overview, type Transaction, type User } from "./lib/api";
import { toast } from "sonner";

const links = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/transactions", label: "Transactions", icon: CreditCard },
  { to: "/app/import", label: "Import statement", icon: FileUp },
  { to: "/app/goals", label: "Goals & budgets", icon: Target },
  { to: "/app/recurring", label: "Recurring", icon: CalendarDays },
  { to: "/app/insights", label: "Insights", icon: TrendingUp },
  { to: "/app/assistant", label: "Ask FinSight", icon: Sparkles },
  { to: "/app/learn", label: "Learn", icon: BookOpen },
  { to: "/app/settings", label: "Settings", icon: Settings },
];
let displayTimezone = "Asia/Kolkata";
const formatMoney = (value: string | number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
const prettyDate = (value: string) =>
  new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: displayTimezone }).format(new Date(`${value}T12:00:00Z`));

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [mobileNav, setMobileNav] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const preferences = useQuery({ queryKey: ["settings"], queryFn: () => api<{ timezone: string }>("/api/v1/settings"), enabled: Boolean(user) });

  useEffect(() => {
    api<User>("/api/v1/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setChecking(false));
  }, []);
  useEffect(() => { if (preferences.data?.timezone) displayTimezone = preferences.data.timezone; }, [preferences.data]);

  async function signOut() {
    await api<void>("/api/v1/auth/logout", { method: "POST" });
    setUser(null);
    queryClient.clear();
    navigate("/");
  }
  if (checking) return <div className="boot"><span className="brand-mark">f</span><LoaderCircle className="spin" size={19} /></div>;

  return (
    <Routes>
      <Route path="/" element={user ? <NavigateTo to="/app" /> : <Landing />} />
      <Route path="/auth" element={user ? <NavigateTo to="/app" /> : <AuthPage onAuth={setUser} />} />
      <Route path="/app/*" element={user ? (
        <div className="app-shell">
          <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
            <Link to="/app" className="brand"><span className="brand-mark">f</span><span>finsight<span className="brand-ai"> AI</span></span></Link>
            <div className="workspace-label">YOUR WORKSPACE</div>
            <nav>{links.map(({ to, label, icon: Icon, end }) => (
              <NavLink end={end} key={to} to={to} onClick={() => setMobileNav(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                <Icon size={18} strokeWidth={1.8} /><span>{label}</span>{label === "Ask FinSight" && <span className="nav-new">AI</span>}
              </NavLink>
            ))}</nav>
            <div className="sidebar-bottom">
              <div className="privacy-note"><ShieldCheck size={17} /><span>Your data stays yours.<small>Private by design</small></span></div>
              <button className="user-menu" onClick={signOut}><span className="avatar">{user.email[0].toUpperCase()}</span><span className="user-name">{user.email}<small>Personal account</small></span><LogOut size={16} /></button>
            </div>
          </aside>
          {mobileNav && <button aria-label="Close navigation" className="nav-scrim" onClick={() => setMobileNav(false)} />}
          <main className="main-area">
            <header className="topbar">
              <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNav(true)}><Menu size={20} /></button>
              <div className="breadcrumbs">Workspace <span>/</span> {titleFromPath(location.pathname)}</div>
              <div className="topbar-right"><span className="demo-badge"><span /> Personal workspace</span><button className="top-avatar" aria-label="Sign out" onClick={signOut}>{user.email[0].toUpperCase()}</button></div>
            </header>
            <div className="page-content">
              <Routes>
                <Route index element={<Dashboard />} />
                <Route path="transactions" element={<Transactions />} />
                <Route path="import" element={<ImportPage />} />
                <Route path="goals" element={<Goals />} />
                <Route path="recurring" element={<Recurring />} />
                <Route path="insights" element={<Insights />} />
                <Route path="assistant" element={<Assistant />} />
                <Route path="learn" element={<Learn />} />
                <Route path="settings" element={<SettingsPage onSignOut={signOut} />} />
                <Route path="*" element={<Dashboard />} />
              </Routes>
            </div>
            <footer className="app-footer">Informational use only · Not investment, tax or lending advice <span>•</span> Live bank connections aren’t available in this MVP</footer>
          </main>
        </div>
      ) : <NavigateTo to="/auth" />} />
      <Route path="*" element={<NavigateTo to="/" />} />
    </Routes>
  );
}

function NavigateTo({ to }: { to: string }) {
  const navigate = useNavigate();
  useEffect(() => { navigate(to, { replace: true }); }, [navigate, to]);
  return null;
}

function titleFromPath(path: string) {
  const hit = links.find((link) => link.to === path);
  return hit?.label ?? (path.split("/").pop()?.replace(/^\w/, (letter) => letter.toUpperCase()) || "Overview");
}

function Landing() {
  return <div className="landing">
    <header className="landing-nav"><Link to="/" className="brand"><span className="brand-mark">f</span><span>finsight<span className="brand-ai"> AI</span></span></Link><a href="#how-it-works">How it works</a><div><Link className="sign-in-link" to="/auth">Sign in</Link><Link className="button button-dark" to="/auth">Explore demo <ArrowRight size={16} /></Link></div></header>
    <section className="hero">
      <div className="hero-copy"><span className="eyebrow"><span className="eyebrow-dot" /> MONEY, MADE CLEARER</span><h1>Understand your money.<br /><em>Make informed decisions.</em></h1><p>Bring your transactions into focus. Explore your spending, plan your next goal, and get clear answers grounded in your own data.</p><div className="hero-actions"><Link to="/auth" className="button button-teal">Explore demo <ArrowRight size={17} /></Link><a href="#how-it-works" className="text-link">See how it works <ArrowRight size={15} /></a></div><div className="hero-assurance"><ShieldCheck size={15} /> Private by design <span>·</span> No bank login required</div></div>
      <div className="hero-preview"><div className="preview-window"><div className="preview-top"><div className="window-dots"><i /><i /><i /></div><span>YOUR FINANCIAL OVERVIEW</span><span className="preview-period">September <ChevronDown size={12} /></span></div><div className="preview-balance"><span>Total expenses</span><b>₹42,680<span>.00</span></b><small><span>↓ 8.2%</span> compared to last month</small></div><div className="preview-chart"><div className="chart-y"><span>₹20k</span><span>₹10k</span><span>₹0</span></div><div className="chart-lines"><i /><i /><i /><svg viewBox="0 0 470 160" preserveAspectRatio="none" aria-label="Illustrative spending trend"><path d="M0,118 C28,111 36,78 76,91 S125,120 156,73 S209,61 234,82 S286,128 312,76 S358,59 390,40 S438,62 470,22" fill="none" stroke="#2c8c82" strokeWidth="3" /><path d="M0,118 C28,111 36,78 76,91 S125,120 156,73 S209,61 234,82 S286,128 312,76 S358,59 390,40 S438,62 470,22 L470,160 L0,160Z" fill="url(#area)" opacity=".13" /><defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#2c8c82" /><stop offset="1" stopColor="#fff" /></linearGradient></defs></svg></div></div><div className="preview-months"><span>1 Sep</span><span>8 Sep</span><span>15 Sep</span><span>22 Sep</span><span>30 Sep</span></div><div className="preview-categories"><div><span className="mini-dot food" /><span>Food & dining</span><b>₹8,450</b></div><div><span className="mini-dot home" /><span>Housing</span><b>₹15,000</b></div><div><span className="mini-dot transport" /><span>Transport</span><b>₹3,280</b></div><div className="preview-disclaimer">Illustrative demo preview</div></div></div><div className="floating-note"><span className="note-icon"><Sparkles size={16} /></span><span>Spending insight<small>See what changed, and why.</small></span></div></div>
    </section>
    <section className="trust-strip"><span>BUILT FOR CLARITY</span><i /><p>Practical tools for everyday financial decisions</p><div><span><Check size={14} /> No bank credentials</span><span><Check size={14} /> Your data, in context</span><span><Check size={14} /> Clear calculations</span></div></section>
    <section className="landing-features" id="how-it-works"><span className="eyebrow">A CALMER WAY TO SEE THE DETAILS</span><h2>Your finances, all in one clearer picture.</h2><p>Start with a statement or a manual entry. FinSight helps you understand the numbers, without connecting to your bank account.</p><div className="feature-grid">{[
      [Wallet, "See where it goes", "Understand your income, spending and category trends with transparent calculations."],
      [FileUp, "Bring your data", "Import a text-based PDF statement or CSV. Review every extracted transaction before it’s saved."],
      [Bot, "Ask useful questions", "Get deterministic answers about your own records, plus educational resources with source links."],
    ].map(([Icon, title, text]) => <article key={title as string}><span className="feature-icon"><Icon size={20} /></span><h3>{title as string}</h3><p>{text as string}</p></article>)}</div></section>
    <section className="landing-privacy"><div><span className="eyebrow">PRIVACY IS THE STARTING POINT</span><h2>Your financial data deserves care.</h2><p>FinSight never asks for bank passwords, OTPs or UPI PINs. Statement files are processed for review; raw uploads aren’t kept as a permanent archive.</p><Link to="/auth" className="text-link">Explore the privacy approach <ArrowRight size={15} /></Link></div><div className="privacy-card"><ShieldCheck size={22} /><b>Designed to be transparent</b><span>Every calculation can be traced to your records.</span><span>Live bank integrations aren’t available in this MVP.</span></div></section>
    <footer className="landing-footer"><Link to="/" className="brand"><span className="brand-mark">f</span><span>finsight<span className="brand-ai"> AI</span></span></Link><span>Understand your money. Make informed decisions.</span><span>Informational use only · Not financial advice</span></footer>
  </div>;
}

const authSchema = z.object({ email: z.string().email("Enter a valid email"), password: z.string().min(10, "Use at least 10 characters") });
type AuthValues = z.infer<typeof authSchema>;
function AuthPage({ onAuth }: { onAuth: (user: User) => void }) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const { register: field, handleSubmit, formState: { errors } } = useForm<AuthValues>({ resolver: zodResolver(authSchema) });
  const navigate = useNavigate();
  async function submit(values: AuthValues) {
    setBusy(true);
    try {
      if (register) await api<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(values) });
      const user = await api<User>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(values) });
      onAuth(user); navigate("/app");
    } catch (error) { toast.error(error instanceof Error ? error.message : "Unable to sign in"); }
    finally { setBusy(false); }
  }
  return <div className="auth-page"><Link to="/" className="brand auth-brand"><span className="brand-mark">f</span><span>finsight<span className="brand-ai"> AI</span></span></Link><div className="auth-card"><span className="eyebrow">YOUR MONEY, IN FOCUS</span><h1>{register ? "Create your account" : "Welcome back"}</h1><p>Use an email and password to keep your workspace private.</p><form onSubmit={handleSubmit(submit)}><label>Email address<input type="email" autoComplete="email" placeholder="you@example.com" {...field("email")} />{errors.email && <small className="field-error">{errors.email.message}</small>}</label><label>Password<input type="password" autoComplete={register ? "new-password" : "current-password"} placeholder="At least 10 characters" {...field("password")} />{errors.password && <small className="field-error">{errors.password.message}</small>}</label><button className="button button-dark full-button" disabled={busy}>{busy && <LoaderCircle className="spin" size={16} />}{register ? "Create account" : "Sign in"} <ArrowRight size={16} /></button></form><div className="auth-switch">{register ? "Already have an account?" : "New to FinSight?"} <button onClick={() => setRegister(!register)}>{register ? "Sign in" : "Create account"}</button></div><div className="auth-note"><ShieldCheck size={16} /> No bank connection or credentials required.</div></div><p className="auth-legal">Your account is for personal financial analysis. Not a bank or investment adviser.</p></div>;
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}
function Loading() { return <div className="loading-state"><LoaderCircle className="spin" /> Loading your data…</div>; }
function ErrorState({ message }: { message: string }) { return <div className="error-state"><CircleHelp size={19} /><div><b>We couldn’t load this view</b><span>{message}</span></div></div>; }

function Dashboard() {
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
    <PageHeading eyebrow={new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date()).toUpperCase()} title="Your financial overview" description="A clear look at the money moving through your life." action={<Link className="button button-outline" to="/app/import"><Plus size={16} /> Add transactions</Link>} />
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
      {transactions.isError ? <ErrorState message={transactions.error.message} /> : transactions.data?.items.length ? <TransactionTable rows={transactions.data.items} /> : <EmptyState icon={<CalendarDays />} title="A fresh start" text="No transactions yet. Import a bank statement or add one manually." action={<Link className="button button-outline" to="/app/import">Import statement <ArrowRight size={15} /></Link>} />}
    </section>
    <div className="dashboard-note"><ShieldCheck size={16} /><span>These totals reflect transactions you’ve entered or imported. FinSight doesn’t connect to your bank.</span></div>
  </>;
}

function Metric({ icon, label, value, helper, tone }: { icon: ReactNode; label: string; value: string; helper: string; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><span className="metric-label">{label}</span><b className="metric-value">{value}</b><small>{helper}</small></article>;
}
function EmptyState({ icon, title, text, action }: { icon: ReactNode; title: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><span>{icon}</span><b>{title}</b><p>{text}</p>{action}</div>;
}
function TransactionTable({ rows, onEdit, onDelete }: { rows: Transaction[]; onEdit?: (row: Transaction) => void; onDelete?: (row: Transaction) => void }) {
  return <div className="table-scroll"><table className="transaction-table"><thead><tr><th>TRANSACTION</th><th>DATE</th><th>CATEGORY</th><th className="align-right">AMOUNT</th>{onEdit && <th>MANAGE</th>}</tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td><span className={`tx-icon ${row.direction === "credit" ? "credit" : ""}`}>{row.direction === "credit" ? <ArrowDownLeft size={15} /> : <ArrowUpRight size={15} />}</span><span className="tx-title">{row.description}<small>{row.tx_type === "transfer" ? "Transfer" : row.direction === "credit" ? "Money in" : "Money out"}</small></span></td><td>{prettyDate(row.date)}</td><td><span className="category-tag">{row.category}</span></td><td className={`align-right amount ${row.direction === "credit" ? "amount-credit" : ""}`}>{row.direction === "credit" ? "+" : "−"}{formatMoney(row.amount)}</td>{onEdit && <td><div className="row-actions"><button aria-label={`Edit ${row.description}`} onClick={() => onEdit(row)}><Pencil size={14} /></button><button aria-label={`Delete ${row.description}`} onClick={() => onDelete?.(row)}><Trash2 size={14} /></button></div></td>}</tr>)}</tbody></table></div>;
}

function Transactions() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [page, setPage] = useState(1);
  const client = useQueryClient();
  const result = useQuery({ queryKey: ["transactions", query, page], queryFn: () => api<{ total: number; items: Transaction[] }>(`/api/v1/transactions?q=${encodeURIComponent(query)}&page=${page}&page_size=20`) });
  const create = useMutation({ mutationFn: (body: object) => api<Transaction>("/api/v1/transactions", { method: "POST", body: JSON.stringify(body) }), onSuccess: () => { client.invalidateQueries({ queryKey: ["transactions"] }); client.invalidateQueries({ queryKey: ["overview"] }); setOpen(false); toast.success("Transaction added"); } });
  const update = useMutation({ mutationFn: (body: object) => api<Transaction>(`/api/v1/transactions/${editing!.id}`, { method: "PATCH", body: JSON.stringify(body) }), onSuccess: () => { client.invalidateQueries(); setOpen(false); setEditing(null); toast.success("Transaction updated"); }, onError: (error: Error) => toast.error(error.message) });
  const remove = useMutation({ mutationFn: (id: string) => api<void>(`/api/v1/transactions/${id}`, { method: "DELETE" }), onSuccess: () => { client.invalidateQueries(); toast.success("Transaction deleted"); }, onError: (error: Error) => toast.error(error.message) });
  return <><PageHeading eyebrow="YOUR RECORDS" title="Transactions" description="Review, search and manage your recorded activity." action={<button className="button button-teal" onClick={() => setOpen(true)}><Plus size={16} /> Add transaction</button>} />
    <section className="card transactions-page"><div className="filter-row"><label className="search-field"><Search size={16} /><input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Search descriptions" /></label><a href={`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1/transactions/export`} className="button button-outline">Export CSV</a></div>
      {result.isLoading ? <Loading /> : result.isError ? <ErrorState message={result.error.message} /> : result.data?.items.length ? <><TransactionTable rows={result.data.items} onEdit={(row) => { setEditing(row); setOpen(true); }} onDelete={(row) => { if (window.confirm(`Delete “${row.description}”?`)) remove.mutate(row.id); }} /><div className="pagination"><span>{result.data.total} transactions</span><div><button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button disabled={page * 20 >= result.data.total} onClick={() => setPage(page + 1)}>Next</button></div></div></> : <EmptyState icon={<CreditCard />} title={query ? "No matching transactions" : "No transactions yet"} text={query ? "Try a different search." : "Add a transaction manually or import a statement."} />}
    </section>
    {open && <Modal title={editing ? "Edit transaction" : "Add transaction"} close={() => { setOpen(false); setEditing(null); }}><TransactionForm initial={editing ?? undefined} onSubmit={(values) => editing ? update.mutate(values) : create.mutate(values)} busy={editing ? update.isPending : create.isPending} error={editing ? update.error?.message : create.error?.message} /></Modal>}
  </>;
}
const txSchema = z.object({ date: z.string().min(1), description: z.string().min(1).max(300), amount: z.string().regex(/^\d+(\.\d{1,2})?$/, "Enter a positive amount"), direction: z.enum(["debit", "credit"]), category: z.string().optional() });
function TransactionForm({ initial, onSubmit, busy, error }: { initial?: Partial<Transaction>; onSubmit: (v: z.infer<typeof txSchema>) => void; busy: boolean; error?: string }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof txSchema>>({ resolver: zodResolver(txSchema), defaultValues: { date: initial?.date ?? new Date().toISOString().slice(0, 10), description: initial?.description ?? "", amount: initial?.amount ?? "", direction: initial?.direction ?? "debit", category: initial?.category ?? "" } });
  return <form className="modal-form" onSubmit={handleSubmit(onSubmit)}><label>Date<input type="date" {...register("date")} /></label><label>Description<input placeholder="e.g. Grocery shopping" {...register("description")} />{errors.description && <small className="field-error">{errors.description.message}</small>}</label><div className="form-row"><label>Amount (₹)<input inputMode="decimal" placeholder="0.00" {...register("amount")} />{errors.amount && <small className="field-error">{errors.amount.message}</small>}</label><label>Direction<select {...register("direction")}><option value="debit">Expense</option><option value="credit">Income / credit</option></select></label></div><label>Category<input placeholder="Auto-categorized if empty" {...register("category")} /></label>{error && <div className="form-error">{error}</div>}<button className="button button-dark full-button" disabled={busy}>{busy ? "Saving…" : initial ? "Save changes" : "Save transaction"} <ArrowRight size={15} /></button></form>;
}
function Modal({ title, close, children }: { title: string; close: () => void; children: ReactNode }) {
  useEffect(() => { const listener = (event: KeyboardEvent) => event.key === "Escape" && close(); window.addEventListener("keydown", listener); return () => window.removeEventListener("keydown", listener); }, [close]);
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && close()}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-heading"><h2 id="modal-title">{title}</h2><button className="icon-button" onClick={close} aria-label="Close"><X size={18} /></button></div>{children}</section></div>;
}

function ImportPage() {
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

function Assistant() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<{ answer: string; mode: string; calculation: { metric: string; value: string; currency: string; date_range: { start: string; end: string }; definition: string; transaction_count?: number } | null; citations: { id: string; title: string; href: string; source_type: string; reference_url: string }[] } | null>(null);
  const query = useMutation({ mutationFn: (text: string) => api<NonNullable<typeof result>>("/api/v1/assistant/query", { method: "POST", body: JSON.stringify({ question: text }) }), onSuccess: setResult, onError: (error: Error) => toast.error(error.message) });
  function ask(text: string) { setQuestion(text); query.mutate(text); }
  return <><PageHeading eyebrow="GROUNDED IN YOUR RECORDS" title="Ask FinSight" description="Get clear calculations from your transaction history, or explore financial topics." />
    <div className="assistant-layout"><section className="card assistant-card"><div className="assistant-messages">{!result && <div className="assistant-welcome"><span className="assistant-spark"><Sparkles size={21} /></span><h2>What would you like to understand?</h2><p>Your personal finance answers use your records and deterministic calculations. Educational answers retrieve local notes and show their sources.</p><div className="suggestions">{["How much did I spend this month?", "How much did I spend on food last month?", "Explain compound interest in simple language."].map((text) => <button onClick={() => ask(text)} key={text}>{text}<ArrowRight size={14} /></button>)}</div></div>}{result && <div className="assistant-answer"><div className="assistant-user-msg">{question}</div><div className="assistant-response"><span className="assistant-spark"><Sparkles size={15} /></span><div><span className="answer-mode">{result.mode === "local_retrieval" ? "RETRIEVED EDUCATIONAL NOTE" : "DETERMINISTIC CALCULATION"}</span><p>{result.answer}</p>{result.calculation && <div className="calculation-card"><div><span>Metric</span><b>{result.calculation.metric.replaceAll("_", " ")}</b></div><div><span>Value</span><b>{formatMoney(result.calculation.value)}</b></div><div><span>Date range</span><b>{result.calculation.date_range.start} — {result.calculation.date_range.end}</b></div><small>{result.calculation.definition}</small></div>}{result.citations.length > 0 && <div className="citation-list"><b>Retrieved sources</b>{result.citations.map((citation) => <a key={citation.id} href={`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}${citation.href}`} target="_blank" rel="noreferrer"><BookOpen size={14} /><span>{citation.title}<small>{citation.source_type} · Further reading: RBI financial education</small></span><ArrowRight size={13} /></a>)}</div>}</div></div></div>}</div><form className="assistant-input" onSubmit={(event: FormEvent) => { event.preventDefault(); if (question.trim()) query.mutate(question); }}><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about your transactions or a money topic…" /><button className="button button-teal" disabled={!question.trim() || query.isPending}>{query.isPending ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}<span>Ask</span></button></form><p className="assistant-disclaimer">FinSight is informational, not individualized investment, lending or tax advice.</p></section><aside className="assistant-aside"><div className="card"><span className="eyebrow">HOW ANSWERS WORK</span><h3>Your data stays the source of truth.</h3><p>Calculations are performed by validated operations on your signed-in account. Educational answers retrieve locally curated notes.</p><div className="aside-divider" /><div className="aside-point"><Check size={15} /> User-scoped transaction records</div><div className="aside-point"><Check size={15} /> Fixed-precision money calculations</div><div className="aside-point"><Check size={15} /> Transfers excluded from spending totals</div><Link className="small-link" to="/app/learn">Explore the knowledge library <ArrowRight size={13} /></Link></div><div className="mock-note"><Bot size={18} /><span><b>Local assistant mode</b><small>Deterministic calculations + lexical retrieval. No LLM API key needed.</small></span></div></aside></div>
  </>;
}

function Learn() {
  const documents = useQuery({ queryKey: ["knowledge"], queryFn: () => api<{ id: string; title: string; topic: string; source_type: string; reference_url: string; updated_at: string }[]>("/api/v1/knowledge/documents") });
  return <><PageHeading eyebrow="FINANCIAL EDUCATION" title="Learn at your own pace" description="Plain-language notes to help you understand common money topics." /><section className="knowledge-grid">{documents.isLoading ? <Loading /> : documents.isError ? <ErrorState message={documents.error.message} /> : documents.data?.map((document) => <article className="card knowledge-card" key={document.id}><span className="knowledge-icon"><BookOpen size={18} /></span><span className="eyebrow">{document.topic}</span><h2>{document.title}</h2><p>FinSight-authored general education note. Not individualized financial advice.</p><div className="knowledge-meta">Updated {document.updated_at}</div><a href={document.reference_url} target="_blank" rel="noreferrer" className="small-link">RBI financial education <ArrowRight size={13} /></a></article>)}</section><div className="dashboard-note"><ShieldCheck size={16} /><span>Notes are written for general learning. External reference links are provided for further reading and do not imply endorsement of a particular financial product.</span></div></>;
}

function Insights() {
  const insights = useQuery({ queryKey: ["insights"], queryFn: () => api<{ items: { title: string; detail: string; method: string; type: string }[]; anomaly_candidates: { transaction_id: string; date: string; description: string; amount: string; category: string; reason: string; warning: string }[]; limitations: string[] }>("/api/v1/insights") });
  const forecast = useQuery({ queryKey: ["forecast"], queryFn: () => api<{ available: boolean; message?: string; estimate?: string; method?: string; history_months?: string[]; warning?: string }>("/api/v1/forecasts") });
  return <><PageHeading eyebrow="PATTERNS, NOT CERTAINTY" title="Financial insights" description="Transparent observations based on the records you’ve provided." />{insights.isLoading || forecast.isLoading ? <Loading /> : insights.isError ? <ErrorState message={insights.error.message} /> : <div className="insights-grid"><section className="card goals-card"><span className="eyebrow">RECORDED TRENDS</span><h2>What changed</h2>{insights.data?.items.length ? insights.data.items.map((item) => <article className="insight-item" key={item.type}><span className="insight-icon"><TrendingUp size={17} /></span><div><b>{item.title}</b><p>{item.detail}</p><small>Method: {item.method}</small></div></article>) : <EmptyState icon={<TrendingUp />} title="More history, clearer patterns" text="Record activity across two months to see a spending comparison." />}<div className="aside-divider" /><span className="eyebrow">UNUSUAL TRANSACTION CANDIDATES</span>{insights.data?.anomaly_candidates.length ? insights.data.anomaly_candidates.map((item) => <article className="insight-item" key={item.transaction_id}><span className="insight-icon warning"><CircleHelp size={17} /></span><div><b>{item.description} · {formatMoney(item.amount)}</b><p>{item.reason} {item.warning}</p><small>{prettyDate(item.date)} · {item.category}</small></div></article>) : <p className="muted">No unusual transactions flagged. At least five same-category debits are needed for a baseline.</p>}<p className="muted">{insights.data?.limitations.join(" ")}</p></section><section className="card goals-card forecast-card"><span className="eyebrow">SPENDING BASELINE</span><h2>Month-end forecast</h2>{forecast.isError ? <ErrorState message={forecast.error.message} /> : forecast.data?.available ? <><div className="forecast-value">{formatMoney(forecast.data.estimate ?? "0")}</div><p>{forecast.data.method}</p><div className="forecast-history">{forecast.data.history_months?.map((month) => <span key={month}>{month}</span>)}</div><div className="review-warning">{forecast.data.warning}</div></> : <EmptyState icon={<TrendingUp />} title="Not enough complete history" text={forecast.data?.message ?? "More monthly records are needed."} />}</section></div>}</>;
}

function Recurring() {
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

function Goals() {
  const client = useQueryClient();
  const budgets = useQuery({ queryKey: ["budgets"], queryFn: () => api<{ id: string; category: string; amount: string; period_start: string; spent: string; usage: string }[]>("/api/v1/budgets") });
  const goals = useQuery({ queryKey: ["goals"], queryFn: () => api<{ id: string; name: string; target_amount: string; saved_amount: string; progress: string; target_date: string | null }[]>("/api/v1/goals") });
  const [goalName, setGoalName] = useState("");
  const [target, setTarget] = useState("");
  const [budgetCategory, setBudgetCategory] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const createGoal = useMutation({ mutationFn: () => api("/api/v1/goals", { method: "POST", body: JSON.stringify({ name: goalName, target_amount: target, saved_amount: "0" }) }), onSuccess: () => { setGoalName(""); setTarget(""); client.invalidateQueries({ queryKey: ["goals"] }); toast.success("Goal created"); }, onError: (error: Error) => toast.error(error.message) });
  const createBudget = useMutation({ mutationFn: () => api("/api/v1/budgets", { method: "POST", body: JSON.stringify({ category: budgetCategory, amount: budgetAmount, period_start: new Date().toISOString().slice(0, 8) + "01" }) }), onSuccess: () => { setBudgetCategory(""); setBudgetAmount(""); client.invalidateQueries({ queryKey: ["budgets"] }); toast.success("Budget created"); }, onError: (error: Error) => toast.error(error.message) });
  return <><PageHeading eyebrow="PLAN WITH PURPOSE" title="Goals & budgets" description="Make a plan for what matters next. Your progress reflects the values you enter." /><div className="goals-grid"><section className="card goals-card"><div className="card-heading"><div><span className="eyebrow">SAVINGS GOALS</span><h2>What are you working toward?</h2></div><Target size={19} /></div>{goals.isLoading ? <Loading /> : goals.data?.length ? <div className="goal-list">{goals.data.map((goal) => <div className="goal-item" key={goal.id}><div className="goal-top"><span className="goal-icon"><Target size={17} /></span><div><b>{goal.name}</b><small>{formatMoney(goal.saved_amount)} saved of {formatMoney(goal.target_amount)}</small></div><button className="text-danger" onClick={() => api(`/api/v1/goals/${goal.id}`, { method: "DELETE" }).then(() => client.invalidateQueries({ queryKey: ["goals"] }))}>Remove</button></div><div className="progress-track"><i style={{ width: `${Math.max(0, Math.min(Number(goal.progress) * 100, 100))}%` }} /></div></div>)}</div> : <EmptyState icon={<Target />} title="No goals yet" text="Create a savings goal to give your progress a purpose." />}<form className="inline-create" onSubmit={(e) => { e.preventDefault(); createGoal.mutate(); }}><input value={goalName} onChange={(e) => setGoalName(e.target.value)} placeholder="Goal name" required /><input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Target (₹)" inputMode="decimal" required /><button className="button button-teal" disabled={createGoal.isPending}><Plus size={15} /> Add goal</button></form></section>
    <section className="card goals-card"><div className="card-heading"><div><span className="eyebrow">MONTHLY BUDGETS</span><h2>Set a spending guide</h2></div><Wallet size={19} /></div>{budgets.isLoading ? <Loading /> : budgets.data?.length ? <div className="goal-list">{budgets.data.map((budget) => <div className="goal-item" key={budget.id}><div className="goal-top"><span className="goal-icon budget"><Wallet size={17} /></span><div><b>{budget.category}</b><small>{formatMoney(budget.spent)} used · from {prettyDate(budget.period_start)}</small></div><strong>{formatMoney(budget.amount)}</strong></div><div className="progress-track"><i style={{ width: `${Math.min(Number(budget.usage) * 100, 100)}%` }} /></div></div>)}</div> : <EmptyState icon={<Wallet />} title="No budgets yet" text="Add a monthly guide for a category you want to keep an eye on." />}<form className="inline-create budget-create" onSubmit={(e) => { e.preventDefault(); createBudget.mutate(); }}><input value={budgetCategory} onChange={(e) => setBudgetCategory(e.target.value)} placeholder="Category" required /><input value={budgetAmount} onChange={(e) => setBudgetAmount(e.target.value)} placeholder="Monthly limit (₹)" inputMode="decimal" required /><button className="button button-teal" disabled={createBudget.isPending}><Plus size={15} /> Add budget</button></form><small className="muted">Budget usage sums recorded same-category debits for the budget month; transfers are excluded.</small></section></div></>;
}

function SettingsPage({ onSignOut }: { onSignOut: () => Promise<void> }) {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<{ currency: string; timezone: string; bank_connectivity: string }>("/api/v1/settings") });
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  useEffect(() => { if (settings.data) setTimezone(settings.data.timezone); }, [settings.data]);
  async function save() { try { await api("/api/v1/settings", { method: "PATCH", body: JSON.stringify({ timezone }) }); displayTimezone = timezone; await queryClient.invalidateQueries({ queryKey: ["settings"] }); toast.success("Preferences saved"); } catch (error) { toast.error(error instanceof Error ? error.message : "Unable to save"); } }
  async function removeTransactions() { if (!window.confirm("Permanently delete all your transactions? This cannot be undone.")) return; try { await api("/api/v1/settings/transactions", { method: "DELETE" }); await queryClient.invalidateQueries(); toast.success("Transaction history deleted"); } catch (error) { toast.error(error instanceof Error ? error.message : "Unable to delete data"); } }
  async function downloadExport() { try { const data = await api<unknown>("/api/v1/settings/export", { method: "POST" }); const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); link.download = "finsight-export.json"; link.click(); URL.revokeObjectURL(link.href); } catch (error) { toast.error(error instanceof Error ? error.message : "Export failed"); } }
  return <><PageHeading eyebrow="YOUR ACCOUNT" title="Settings & privacy" description="Manage the details that shape your workspace." /><div className="settings-layout"><section className="card settings-card"><span className="eyebrow">PREFERENCES</span><h2>Regional settings</h2><p>Transactions are stored in INR; currency conversion is not applied in this MVP.</p>{settings.isError ? <ErrorState message={settings.error.message} /> : <><label>Currency<input value="Indian Rupee (₹ INR)" readOnly /></label><label>Timezone<input value={timezone} onChange={(e) => setTimezone(e.target.value)} /></label><button className="button button-teal" onClick={save}>Save preferences <Check size={15} /></button></>}</section><section className="card settings-card"><span className="eyebrow">DATA & PRIVACY</span><h2>You’re in control</h2><p>Download a copy of your data or remove transaction history from your account.</p><div className="settings-callout"><ShieldCheck size={19} /><span><b>Live bank connections are not available.</b><small>FinSight will never ask for your bank password, OTP or UPI PIN.</small></span></div><div className="settings-actions"><button className="button button-outline" onClick={downloadExport}>Export my data</button><button className="button button-danger-outline" onClick={removeTransactions}>Delete transactions</button></div><div className="settings-actions"><button className="button button-outline" onClick={onSignOut}><LogOut size={15} /> Sign out</button><button className="button button-danger-outline" onClick={async () => { if (!window.confirm("Delete your account and associated data permanently?")) return; await api("/api/v1/settings/account", { method: "DELETE" }); onSignOut(); }}>Delete account</button></div></section></div></>;
}

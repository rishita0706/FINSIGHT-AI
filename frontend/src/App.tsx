import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ArrowRight, BookOpen, Bot, CalendarDays, Check, ChevronDown, CreditCard, FileUp, LayoutDashboard, LoaderCircle, LogOut, Menu, Settings, ShieldCheck, Sparkles, Target, TrendingUp, Wallet } from "lucide-react";
import { api, type User } from "./lib/api";
import { toast } from "sonner";
import { Assistant, Budgets, Dashboard, Goals, ImportHistory, ImportWizard, Insights, Learn, ModelEvaluation, Recurring, SettingsPage, Transactions } from "./features/Pages";

const links = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/transactions", label: "Transactions", icon: CreditCard },
  { to: "/app/import/wizard", label: "Import statement", icon: FileUp, end: true },
  { to: "/app/import/history", label: "Import history", icon: BookOpen },
  { to: "/app/budgets", label: "Budgets", icon: Wallet },
  { to: "/app/goals", label: "Savings goals", icon: Target },
  { to: "/app/recurring", label: "Recurring", icon: CalendarDays },
  { to: "/app/insights", label: "Insights", icon: TrendingUp },
  { to: "/app/model-evaluation", label: "Categorizer evaluation", icon: Sparkles },
  { to: "/app/assistant", label: "Ask FinSight", icon: Sparkles },
  { to: "/app/learn", label: "Learn", icon: BookOpen },
  { to: "/app/settings", label: "Settings", icon: Settings },
];
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [mobileNav, setMobileNav] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  useEffect(() => {
    api<User>("/api/v1/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setChecking(false));
  }, []);

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
                <Route path="import" element={<ImportWizard />} />
                <Route path="import/wizard" element={<ImportWizard />} />
                <Route path="import/history" element={<ImportHistory />} />
                <Route path="budgets" element={<Budgets />} />
                <Route path="goals" element={<Goals />} />
                <Route path="recurring" element={<Recurring />} />
                <Route path="insights" element={<Insights />} />
                <Route path="model-evaluation" element={<ModelEvaluation />} />
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

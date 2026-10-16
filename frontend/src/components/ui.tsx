import type { ReactNode } from "react";
import { CircleHelp, LoaderCircle } from "lucide-react";

export function PageHeading({ eyebrow, title, description, action }: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return <div className="page-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}

export function Loading() {
  return <div className="loading-state"><LoaderCircle className="spin" /> Loading your data…</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="error-state"><CircleHelp size={19} /><div><b>We couldn’t load this view</b><span>{message}</span></div></div>;
}

export function Metric({ icon, label, value, helper, tone }: {
  icon: ReactNode;
  label: string;
  value: string;
  helper: string;
  tone: string;
}) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><span className="metric-label">{label}</span><b className="metric-value">{value}</b><small>{helper}</small></article>;
}

export function EmptyState({ icon, title, text, action }: {
  icon: ReactNode;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return <div className="empty-state"><span>{icon}</span><b>{title}</b><p>{text}</p>{action}</div>;
}

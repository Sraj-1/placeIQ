import type { ReactNode } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";

/* ── Surfaces ─────────────────────────────────────────────────────────────── */

export function Card({ className, accent, children, ...rest }: React.HTMLAttributes<HTMLElement> & { accent?: boolean }) {
  return (
    <section
      className={cn(
        "relative min-w-0 overflow-hidden rounded-2xl border border-border bg-surface/60 p-5",
        accent && "bg-gradient-to-br from-brand/10 via-transparent to-transparent bg-origin-border shadow-lg",
        className,
      )}
      {...rest}
    >
      {children}
    </section>
  );
}

export function CardTitle({ children, action }: { children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      {children && <h2 className="text-base font-semibold text-foreground">{children}</h2>}
      {action}
    </div>
  );
}

/** A Card with top spacing and an optional title row: the standard page section. */
export function Section({ title, action, className, children, id }: { title?: ReactNode; action?: ReactNode; className?: string; children: ReactNode; id?: string }) {
  return (
    <Card className={cn("mt-5", className)} id={id}>
      {(title || action) && <CardTitle action={action}>{title}</CardTitle>}
      {children}
    </Card>
  );
}

export function Tiles({ children }: { children: ReactNode }) {
  return <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{children}</div>;
}

export function PageHeader({ eyebrow, title, children, aside }: { eyebrow: string; title: ReactNode; children?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-brand-text">{eyebrow}</p>
        <h1 className="mt-2 font-display text-3xl tracking-tight text-headline sm:text-4xl">{title}</h1>
        {children && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{children}</p>}
      </div>
      {aside && <div className="shrink-0">{aside}</div>}
    </header>
  );
}

/* ── Controls ─────────────────────────────────────────────────────────────── */

const BUTTON = {
  primary: "bg-brand text-brand-foreground hover:bg-brand-hover",
  outline: "border border-border bg-surface text-foreground hover:bg-surface-hover",
  ghost: "text-muted hover:bg-surface-hover hover:text-foreground",
} as const;

export function buttonClass(variant: keyof typeof BUTTON = "primary", size: "md" | "sm" = "md") {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/50 disabled:pointer-events-none disabled:opacity-50",
    size === "md" ? "min-h-10 px-3.5 text-sm" : "min-h-8 px-2.5 text-xs",
    BUTTON[variant],
  );
}

export function Button({ variant = "primary", size = "md", className, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof BUTTON; size?: "md" | "sm" }) {
  return <button type="button" className={cn(buttonClass(variant, size), className)} {...rest} />;
}

export function ButtonLink({ href, variant = "primary", size = "md", className, children }: { href: string; variant?: keyof typeof BUTTON; size?: "md" | "sm"; className?: string; children: ReactNode }) {
  return <Link href={href} className={cn(buttonClass(variant, size), className)}>{children}</Link>;
}

export const inputClass =
  "w-full rounded-md border border-border bg-surface px-2.5 py-2 text-sm text-foreground placeholder:text-faint focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/50";
export const inputCls = inputClass;

export function Field({ label, htmlFor, hint, review, children }: { label: string; htmlFor: string; hint?: string; review?: boolean; children: ReactNode }) {
  return (
    <div className={cn("min-w-0", review && "[&_input]:border-amber-500 [&_input]:bg-amber-500/10 [&_select]:border-amber-500 [&_select]:bg-amber-500/10")}>
      <label htmlFor={htmlFor} className="mb-1 block text-xs font-semibold text-muted">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-faint">{hint}</p>}
    </div>
  );
}

/* ── Status ───────────────────────────────────────────────────────────────── */

const BADGE = {
  good: "bg-emerald-500/15 text-emerald-800 dark:text-emerald-400",
  warn: "bg-amber-500/15 text-amber-800 dark:text-amber-400",
  bad: "bg-red-500/15 text-red-700 dark:text-red-400",
  info: "bg-sky-500/15 text-sky-800 dark:text-sky-300",
  muted: "bg-surface-hover text-muted",
} as const;

export function Badge({ tone = "muted", className, children }: { tone?: keyof typeof BADGE; className?: string; children: ReactNode }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold tabular-nums", BADGE[tone], className)}>{children}</span>;
}

const NOTICE = {
  warn: "border-amber-500/40 bg-amber-500/10",
  info: "border-sky-500/40 bg-sky-500/10",
  error: "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
  ok: "border-emerald-500/40 bg-emerald-500/10",
} as const;

export function Notice({ tone = "warn", children, className }: { tone?: keyof typeof NOTICE; children: ReactNode; className?: string }) {
  const icon = { warn: "!", info: "i", error: "✕", ok: "✓" }[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cn("flex gap-3 rounded-lg border px-3 py-2.5 text-sm", NOTICE[tone], className)}>
      <span aria-hidden className="font-bold">{icon}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function Band({ p }: { p: number }) {
  if (p >= 0.7) return <Badge tone="good">✓ Ready</Badge>;
  if (p >= 0.4) return <Badge tone="warn">! Borderline</Badge>;
  return <Badge tone="bad">✕ At risk</Badge>;
}

export function Delta({ value, className }: { value: number; className?: string }) {
  if (Math.abs(value) < 0.005) return <span className={cn("text-sm text-faint", className)}>no change</span>;
  const up = value > 0;
  return (
    <span className={cn("whitespace-nowrap text-sm font-semibold tabular-nums", up ? "text-good" : "text-bad", className)}>
      {up ? "▲ +" : "▼ −"}{Math.abs(value * 100).toFixed(1)} pts
    </span>
  );
}

export function Tile({ label, value, hint }: { label: ReactNode; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="min-w-0 rounded-xl border border-border bg-surface/60 p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 break-words text-xs text-faint">{hint}</div>}
    </div>
  );
}

/* ── Charts (plain HTML so they follow the theme) ─────────────────────────── */

export function Meter({ value, label }: { value: number; label: string }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-surface-hover" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)} aria-label={label}>
      <div className="h-full rounded-full bg-brand" style={{ width: `max(${value * 100}%, 2px)` }} />
    </div>
  );
}

export function Gauge({ value, size = 132 }: { value: number; size?: number }) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${Math.round(value * 100)} percent`} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth="12" className="stroke-surface-hover" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth="12" strokeLinecap="round" className="stroke-brand"
        strokeDasharray={`${c * value} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="fill-foreground font-display" fontSize={size * 0.26}>
        {Math.round(value * 100)}%
      </text>
    </svg>
  );
}

type Item = { label: string; value: number; title?: string };

export function Bars({ items, fmt, max, tone = "brand" }: { items: Item[]; fmt: (v: number) => string; max?: number; tone?: "brand" | "pos" | "neg" | "faint" }) {
  const m = max ?? Math.max(...items.map((i) => i.value), 1e-9);
  const color = { brand: "bg-brand", pos: "bg-pos", neg: "bg-neg", faint: "bg-faint/60" }[tone];
  return (
    <div className="grid gap-1">
      {items.map((i) => (
        <div key={i.label} title={i.title} className="grid grid-cols-[minmax(96px,36%)_1fr_48px] items-center gap-2 rounded px-1 py-0.5 hover:bg-surface-hover">
          <span className="truncate text-right text-xs text-muted">{i.label}</span>
          <span className="h-2.5"><span className={cn("block h-full rounded-r", color)} style={{ width: `max(${(i.value / m) * 100}%, 2px)` }} /></span>
          <span className="text-right text-xs tabular-nums text-muted">{fmt(i.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function DivergingBars({ items, fmt, legend }: { items: Item[]; fmt: (v: number) => string; legend: [string, string] }) {
  const lo = Math.min(0, ...items.map((a) => a.value));
  const hi = Math.max(0, ...items.map((a) => a.value));
  const span = hi - lo || 1;
  const pos = (v: number) => ((v - lo) / span) * 100;
  const zero = pos(0);
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5"><i className="inline-block size-2.5 rounded-sm bg-pos" />{legend[0]}</span>
        <span className="inline-flex items-center gap-1.5"><i className="inline-block size-2.5 rounded-sm bg-neg" />{legend[1]}</span>
      </div>
      <div className="grid gap-0.5">
        {items.map((a) => {
          const p = pos(a.value);
          const up = a.value >= 0;
          return (
            <div key={a.label} title={a.title} className="grid grid-cols-[minmax(96px,34%)_1fr] items-center gap-2 rounded px-1 hover:bg-surface-hover">
              <span className="truncate text-right text-xs text-muted">{a.label}</span>
              <div className="relative mx-11 h-6">
                <div className="absolute inset-y-0 w-px bg-border" style={{ left: `${zero}%` }} />
                <div className={cn("absolute top-[7px] h-2.5", up ? "rounded-r bg-pos" : "rounded-l bg-neg")}
                  style={{ left: `${Math.min(p, zero)}%`, width: `max(${Math.abs(p - zero)}%, 2px)` }} />
                <span className="absolute top-1 whitespace-nowrap text-[11px] tabular-nums text-muted"
                  style={up ? { left: `calc(${p}% + 4px)` } : { right: `calc(${100 - p}% + 4px)` }}>{fmt(a.value)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>{head.map((h, i) => <th key={i} className="border-b border-border px-2 py-1.5 text-left text-xs font-semibold text-muted">{h}</th>)}</tr>
        </thead>
        <tbody className="[&_td]:border-b [&_td]:border-border [&_td]:px-2 [&_td]:py-2">{children}</tbody>
      </table>
    </div>
  );
}

export const pct = (v: number) => `${Math.round(v * 100)}%`;
export const n3 = (v: number | null | undefined) => (v === null || v === undefined ? "–" : v.toFixed(3));
export const signed = (v: number, d = 3) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(d)}`;

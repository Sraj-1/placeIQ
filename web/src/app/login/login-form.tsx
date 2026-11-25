"use client";
import { Lock } from "lucide-react";
import { useState } from "react";
import { Button, Card, Field, inputClass, Notice } from "@/components/ui";

export function LoginForm({ next }: { next: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const r = await fetch("/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ password }) });
      if (!r.ok) throw new Error(((await r.json().catch(() => ({}))) as { detail?: string }).detail ?? "Sign-in failed.");
      window.location.assign(next.startsWith("/") && !next.startsWith("//") ? next : "/cell");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <Card accent className="mx-auto mt-8 max-w-md">
      <div className="mb-4 flex items-center gap-2"><Lock className="size-4 text-brand-text" /><h2 className="text-base font-semibold">Placement cell sign-in</h2></div>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Password" htmlFor="pw"><input id="pw" type="password" autoComplete="current-password" autoFocus className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <Button type="submit" disabled={busy || !password}>{busy ? "Signing in…" : "Sign in"}</Button>
      </form>
      {error && <Notice tone="error" className="mt-4">{error}</Notice>}
      <p className="mt-4 text-xs text-faint">Students don&apos;t need to sign in. This area holds batch data and model controls.</p>
    </Card>
  );
}

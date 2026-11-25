"use client";
import { useEffect, useState } from "react";
import { adminApi } from "@/lib/client";

/** A report figure (PNG) from the engine; re-fetched when `version` changes. */
export function Figure({ name, alt, version }: { name: string; alt: string; version?: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let url: string | null = null;
    let alive = true;
    setFailed(false);
    adminApi.figure(name).then((b) => { if (alive) { url = URL.createObjectURL(b); setSrc(url); } }).catch(() => alive && setFailed(true));
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [name, version]);
  if (failed) return <p className="text-sm text-faint">Figure not available yet. Train a model first.</p>;
  if (!src) return <p className="text-sm text-faint">Loading figure…</p>;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className="h-auto w-full rounded-lg bg-white" />;
}

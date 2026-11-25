"use client";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import type { Health } from "@/lib/client";
import { ButtonLink, Card, Notice } from "./ui";

/** Engine/model state notices shown at the top of live pages. Returns true-ish content only when relevant. */
export function EngineStatus({ health, loading }: { health: Health | null; loading: boolean }) {
  if (loading) return null;
  if (!health) {
    return <Notice tone="error" className="mt-5">The PlaceIQ engine isn&apos;t running. Start everything with <code>start.bat</code>.</Notice>;
  }
  if (!health.model_loaded) {
    return <Notice tone="info" className="mt-5">No model has been trained yet. The placement cell can train one on the Model page.</Notice>;
  }
  if (health.model?.synthetic_data) {
    return (
      <Notice className="mt-5">
        <strong>Demo model.</strong> The current model was trained on synthetic data, so estimates are illustrative only.
      </Notice>
    );
  }
  if (health.model?.indicative_only) {
    return <Notice tone="info" className="mt-5">The model was trained on fewer than 150 records, so treat estimates as indicative.</Notice>;
  }
  if (health.model?.public_data) {
    const n = health.model.n_records?.toLocaleString();
    return (
      <p className="mt-4 text-xs text-faint">
        Model trained on {n} students from public placement datasets, not your college&apos;s own records.{" "}
        <Link href="/about#data" className="underline">About the data</Link>
      </p>
    );
  }
  return null;
}

export function NeedProfile() {
  return (
    <Card accent className="mt-5">
      <h2 className="font-display text-3xl text-headline">Let&apos;s set up your profile</h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
        Upload your CV and confirm a few details (branch, CGPA, backlogs). PlaceIQ then estimates your placement readiness,
        explains it, and shows the changes that would help most.
      </p>
      <div className="mt-4"><ButtonLink href="/profile">Set up my profile <ArrowRight className="size-4" /></ButtonLink></div>
    </Card>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <p role="status" className="mt-5 text-sm text-faint">{label}</p>;
}

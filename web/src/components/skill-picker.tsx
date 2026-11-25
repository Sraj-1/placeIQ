"use client";
import { X } from "lucide-react";
import { useState } from "react";
import { inputClass } from "./ui";

/** Skills limited to the PlaceIQ taxonomy, with autocomplete, removable chips and optional suggestions. */
export function SkillPicker({ taxonomy, value, onChange, evidence, suggestions, idPrefix = "skill", label = "Skills" }: {
  taxonomy: Record<string, string>;
  value: string[];
  onChange: (v: string[]) => void;
  evidence?: Record<string, string>;
  suggestions?: string[];
  idPrefix?: string;
  label?: string;
}) {
  const [input, setInput] = useState("");
  const [err, setErr] = useState<string | null>(null);

  function add(raw: string) {
    const s = raw.trim().toLowerCase();
    if (!s) return;
    if (Object.keys(taxonomy).length && !(s in taxonomy)) { setErr(`"${raw}" isn't in the skill list. Pick a suggestion.`); return; }
    setErr(null);
    if (!value.includes(s)) onChange([...value, s].sort());
    setInput("");
  }
  const pending = (suggestions ?? []).filter((s) => !value.includes(s));

  return (
    <div>
      <label htmlFor={`${idPrefix}-input`} className="mb-1 block text-xs font-semibold text-muted">{label} ({value.length})</label>
      <div className="flex gap-2">
        <input id={`${idPrefix}-input`} list={`${idPrefix}-list`} value={input} placeholder="Start typing, e.g. docker" className={inputClass}
          onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(input); } }} />
        <button type="button" onClick={() => add(input)} className="min-h-10 rounded-md border border-border bg-surface px-3 text-sm hover:bg-surface-hover">Add</button>
      </div>
      <datalist id={`${idPrefix}-list`}>
        {Object.keys(taxonomy).filter((s) => !value.includes(s)).map((s) => <option key={s} value={s} />)}
      </datalist>
      {err && <p className="mt-1 text-xs text-bad">{err}</p>}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {value.map((s) => (
          <span key={s} title={evidence?.[s] ? `Found in your CV as "${evidence[s].split(":").slice(1).join(":")}"` : "Added by you"}
            className="inline-flex items-center gap-1 rounded-full bg-surface-hover py-0.5 pl-2.5 pr-1 text-xs">
            {s}
            {evidence?.[s]?.startsWith("fuzzy") && <span className="text-faint">(check)</span>}
            <button type="button" aria-label={`Remove ${s}`} onClick={() => onChange(value.filter((x) => x !== s))} className="rounded-full p-0.5 text-faint hover:text-bad"><X className="size-3" /></button>
          </span>
        ))}
        {value.length === 0 && <span className="text-xs text-faint">No skills yet.</span>}
      </div>
      {pending.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-faint">Suggested:</span>
          {pending.map((s) => (
            <button type="button" key={s} onClick={() => onChange([...value, s].sort())}
              className="rounded-full border border-dashed border-border px-2.5 py-0.5 text-xs text-muted hover:border-brand hover:text-foreground">+ {s}</button>
          ))}
        </div>
      )}
    </div>
  );
}

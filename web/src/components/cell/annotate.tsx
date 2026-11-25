"use client";
// PlaceIQ placement cell: ground-truth annotation tool for the 50-resume extraction study.
import { useCallback, useEffect, useState } from "react";
import { adminApi, type AnnotationSummary, type SkillMatch } from "@/lib/client";
import { Badge, Button, Field, Notice, Section, Table, inputCls } from "@/components/ui";
import { SkillPicker } from "@/components/skill-picker";

const TARGET = 50;

export function CellAnnotate({ taxonomy }: { taxonomy: Record<string, string> }) {
  const [list, setList] = useState<AnnotationSummary[]>([]);
  const [resumeId, setResumeId] = useState("");
  const [text, setText] = useState("");
  const [gold, setGold] = useState<string[]>([]);
  const [predicted, setPredicted] = useState<SkillMatch[]>([]);
  const [annotator, setAnnotator] = useState("");
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { try { setAnnotator(localStorage.getItem("placeiq.annotator") ?? ""); } catch { /* storage blocked */ } }, []);
  const refresh = useCallback(() => adminApi.annotations().then(setList).catch((e) => setMsg({ tone: "error", text: (e as Error).message })), []);
  useEffect(() => { refresh(); }, [refresh]);

  const reset = () => { setResumeId(""); setText(""); setGold([]); setPredicted([]); setEditing(false); };

  async function onPdf(file: File) {
    setBusy(true); setMsg(null);
    try {
      const r = await adminApi.parseForAnnotation(file);
      setText(r.text); setPredicted(r.predicted); setGold([]);
      if (!resumeId) setResumeId(file.name.replace(/\.pdf$/i, "").replace(/[^A-Za-z0-9_.-]/g, "_").slice(0, 64));
    } catch (e) { setMsg({ tone: "error", text: (e as Error).message }); }
    finally { setBusy(false); }
  }
  async function open(id: string) {
    setMsg(null);
    try {
      const a = await adminApi.annotation(id);
      setResumeId(a.resume_id); setText(a.text); setGold(a.gold_skills); setPredicted(a.predicted);
      setAnnotator((x) => x || a.annotator); setEditing(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) { setMsg({ tone: "error", text: (e as Error).message }); }
  }
  async function save() {
    setMsg(null);
    if (!/^[A-Za-z0-9_.-]{1,64}$/.test(resumeId)) { setMsg({ tone: "error", text: 'Resume ID: letters, digits, "_", "-" or "." only.' }); return; }
    if (text.trim().length < 20) { setMsg({ tone: "error", text: "Paste or upload the resume text first." }); return; }
    setBusy(true);
    try {
      try { localStorage.setItem("placeiq.annotator", annotator); } catch { /* ignore */ }
      await adminApi.saveAnnotation(resumeId, text, gold, annotator);
      setMsg({ tone: "ok", text: `Saved ${resumeId} with ${gold.length} gold skills.` });
      reset(); refresh();
    } catch (e) { setMsg({ tone: "error", text: (e as Error).message }); }
    finally { setBusy(false); }
  }
  async function remove(id: string) {
    if (!window.confirm(`Delete annotation ${id}?`)) return;
    try { await adminApi.deleteAnnotation(id); refresh(); if (id === resumeId) reset(); } catch (e) { setMsg({ tone: "error", text: (e as Error).message }); }
  }

  const evidence = Object.fromEntries(predicted.map((p) => [p.skill, `${p.method}:${p.alias}`]));
  return (
    <>
      <Section title="Annotate resumes for the extraction study">
        <p className="text-sm text-muted">
          Label the skills a resume <em>actually</em> contains, using canonical taxonomy names. Label from the text, not from the extractor: its
          suggestions are shown separately so they don&apos;t bias you. Target: {TARGET} resumes ({list.length} saved). Contact details are removed before saving.
        </p>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-hover" aria-label={`${list.length} of ${TARGET} annotated`}>
          <div className="h-full bg-brand" style={{ width: `${Math.min(100, (list.length / TARGET) * 100)}%` }} />
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Field label="Resume ID" htmlFor="ann-id"><input id="ann-id" className={inputCls} value={resumeId} disabled={editing} placeholder="e.g. r001" onChange={(e) => setResumeId(e.target.value)} /></Field>
          <Field label="Annotator initials" htmlFor="ann-who"><input id="ann-who" className={inputCls} maxLength={32} value={annotator} onChange={(e) => setAnnotator(e.target.value)} /></Field>
          <Field label="Load from PDF" htmlFor="ann-pdf"><input id="ann-pdf" type="file" accept="application/pdf,.pdf" className="text-sm" onChange={(e) => { const f = e.target.files?.[0]; if (f) onPdf(f); e.target.value = ""; }} /></Field>
        </div>
        <div className="mt-3">
          <Field label="Resume text" htmlFor="ann-text">
            <textarea id="ann-text" rows={10} className={`${inputCls} font-mono text-xs`} value={text} placeholder="Paste resume text, or load a PDF above" onChange={(e) => setText(e.target.value)} />
          </Field>
        </div>
        <div className="mt-3"><SkillPicker taxonomy={taxonomy} value={gold} onChange={setGold} evidence={evidence} suggestions={predicted.map((p) => p.skill)} idPrefix="gold" /></div>
        <div className="mt-4 flex gap-2">
          <Button onClick={save} disabled={busy}>{editing ? "Update annotation" : "Save annotation"}</Button>
          {(editing || text) && <Button variant="outline" onClick={reset}>Clear</Button>}
        </div>
        {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      </Section>
      <Section title={`Saved annotations (${list.length})`}>
        {list.length === 0 ? <p className="text-sm text-faint">None yet.</p> : (
          <Table head={["Resume ID", "Gold skills", "Annotator", "Updated", ""]}>
            {list.map((a) => (
              <tr key={a.resume_id}>
                <td><button className="text-brand-text underline" onClick={() => open(a.resume_id)}>{a.resume_id}</button></td>
                <td className="tabular-nums">{a.n_gold}</td>
                <td>{a.annotator}</td>
                <td className="text-xs text-faint">{a.updated_at ? new Date(a.updated_at).toLocaleString() : ""}</td>
                <td className="text-right"><button className="text-xs text-red-700 dark:text-red-400 underline dark:text-red-400" onClick={() => remove(a.resume_id)}>Delete</button></td>
              </tr>
            ))}
          </Table>
        )}
      </Section>
    </>
  );
}

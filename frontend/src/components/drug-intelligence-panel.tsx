"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  BellRing,
  BrainCircuit,
  ClipboardCheck,
  FileSearch,
  Fingerprint,
  KeyRound,
  Link2,
  Loader2,
  Network,
  Play,
  Plus,
  Radio,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  correlateInvestigation,
  createIntelligenceSource,
  createInvestigation,
  getCorrelationFindings,
  getDrugSignals,
  getEvidenceItems,
  getIntelligenceEntities,
  getIntelligenceSources,
  getInvestigations,
  reviewDrugSignal,
  runIntelligenceSource,
  setIntelligenceOperatorKey,
} from "@/lib/api";
import type { DrugSignal, Investigation } from "@/lib/types";

const intelligenceKeys = {
  all: ["drug-intelligence"] as const,
  investigations: ["drug-intelligence", "investigations"] as const,
  sources: ["drug-intelligence", "sources"] as const,
  evidence: (investigation: number | null) => ["drug-intelligence", "evidence", investigation] as const,
  signals: (investigation: number | null) => ["drug-intelligence", "signals", investigation] as const,
  entities: ["drug-intelligence", "entities"] as const,
  correlations: (investigation: number | null) => ["drug-intelligence", "correlations", investigation] as const,
};

function when(value: string | null): string {
  if (!value) return "not collected";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function tone(value: string): string {
  if (["high", "escalated"].includes(value)) return "border-red-200 bg-red-50 text-red-800";
  if (["medium", "triaged", "corroborated"].includes(value)) return "border-amber-200 bg-amber-50 text-amber-800";
  if (value === "false_positive") return "border-slate-200 bg-slate-100 text-slate-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-800";
}

export function DrugIntelligencePanel() {
  const queryClient = useQueryClient();
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<number | null>(null);
  const [operatorKey, setOperatorKey] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null);

  const [caseName, setCaseName] = useState("Telegram drug intelligence review");
  const [caseDescription, setCaseDescription] = useState("");
  const [casePriority, setCasePriority] = useState<Investigation["priority"]>("high");
  const [authorizationReference, setAuthorizationReference] = useState("");

  const [sourceName, setSourceName] = useState("Approved Telegram source");
  const [sourcePlatform, setSourcePlatform] = useState<"telegram" | "onion">("telegram");
  const [sourceExternalId, setSourceExternalId] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceAuthorization, setSourceAuthorization] = useState<"pending" | "approved">("pending");
  const [sourceEnabled, setSourceEnabled] = useState(false);
  const [sourceInterval, setSourceInterval] = useState(60);

  const investigationsQuery = useQuery({
    queryKey: intelligenceKeys.investigations,
    queryFn: getInvestigations,
    refetchInterval: 30_000,
  });
  const sourcesQuery = useQuery({
    queryKey: intelligenceKeys.sources,
    queryFn: getIntelligenceSources,
    refetchInterval: 30_000,
  });
  const investigationId = selectedInvestigationId ?? investigationsQuery.data?.[0]?.id ?? null;
  const evidenceQuery = useQuery({
    queryKey: intelligenceKeys.evidence(investigationId),
    queryFn: () => getEvidenceItems(investigationId ?? undefined),
    refetchInterval: 30_000,
  });
  const signalsQuery = useQuery({
    queryKey: intelligenceKeys.signals(investigationId),
    queryFn: () => getDrugSignals(investigationId ?? undefined),
    refetchInterval: 30_000,
  });
  const entitiesQuery = useQuery({
    queryKey: intelligenceKeys.entities,
    queryFn: getIntelligenceEntities,
    refetchInterval: 30_000,
  });
  const correlationsQuery = useQuery({
    queryKey: intelligenceKeys.correlations(investigationId),
    queryFn: () => getCorrelationFindings(investigationId ?? undefined),
    refetchInterval: 30_000,
  });

  const investigations = investigationsQuery.data ?? [];
  const sources = sourcesQuery.data ?? [];
  const evidence = evidenceQuery.data ?? [];
  const signals = signalsQuery.data ?? [];
  const entities = entitiesQuery.data ?? [];
  const correlations = correlationsQuery.data ?? [];
  const selectedSignal = signals.find((signal) => signal.id === selectedSignalId) ?? signals[0] ?? null;
  const [reviewStatus, setReviewStatus] = useState<DrugSignal["review_status"]>("triaged");
  const [reviewNote, setReviewNote] = useState("");
  const [reviewer, setReviewer] = useState("operator");

  useEffect(() => {
    setIntelligenceOperatorKey(operatorKey);
  }, [operatorKey]);

  useEffect(() => {
    if (!selectedInvestigationId && investigations[0]) {
      setSelectedInvestigationId(investigations[0].id);
    }
  }, [investigations, selectedInvestigationId]);

  useEffect(() => {
    if (selectedSignal) {
      setReviewStatus(selectedSignal.review_status);
      setReviewNote(selectedSignal.review_note);
    }
  }, [selectedSignal]);

  const queryError = [
    investigationsQuery.error,
    sourcesQuery.error,
    evidenceQuery.error,
    signalsQuery.error,
    entitiesQuery.error,
    correlationsQuery.error,
  ].find(Boolean);

  const summary = useMemo(
    () => ({
      approved: sources.filter((source) => source.enabled && source.authorization_status === "approved").length,
      review: signals.filter((signal) => signal.review_status === "new").length,
      high: signals.filter((signal) => signal.risk_score >= 70).length,
      correlations: correlations.length,
    }),
    [correlations.length, signals, sources]
  );

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: intelligenceKeys.all });
  }

  async function submitInvestigation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("investigation");
    setMessage("");
    try {
      const created = await createInvestigation({
        name: caseName.trim(),
        description: caseDescription.trim(),
        priority: casePriority,
        authorization_reference: authorizationReference.trim(),
      });
      setSelectedInvestigationId(created.id);
      setMessage("Investigation created.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create investigation.");
    } finally {
      setBusy("");
    }
  }

  async function submitSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("source");
    setMessage("");
    try {
      await createIntelligenceSource({
        investigation: investigationId,
        platform: sourcePlatform,
        external_id: sourceExternalId.trim(),
        display_name: sourceName.trim(),
        public_url: sourceUrl.trim(),
        collection_mode: sourcePlatform === "telegram" ? "bot_webhook" : "manual",
        authorization_status: sourceAuthorization,
        enabled: sourceEnabled,
        interval: Math.max(1, sourceInterval) * 60,
      });
      setMessage("Telegram source registered.");
      setSourceExternalId("");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not register source.");
    } finally {
      setBusy("");
    }
  }

  async function runSource(sourceId: number) {
    setBusy(`source-${sourceId}`);
    setMessage("");
    try {
      await runIntelligenceSource(sourceId);
      setMessage("Source collection dispatched.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not dispatch source.");
    } finally {
      setBusy("");
    }
  }

  async function saveReview() {
    if (!selectedSignal) return;
    setBusy(`signal-${selectedSignal.id}`);
    setMessage("");
    try {
      await reviewDrugSignal(selectedSignal.id, {
        status: reviewStatus,
        reviewer: reviewer.trim() || "operator",
        note: reviewNote.trim(),
      });
      setMessage("Triage decision recorded.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save review.");
    } finally {
      setBusy("");
    }
  }

  async function runCorrelation() {
    if (!investigationId) return;
    setBusy("correlate");
    setMessage("");
    try {
      await correlateInvestigation(investigationId);
      setMessage("Correlation findings refreshed.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not refresh correlations.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-md bg-slate-900 text-white">
            <BrainCircuit className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-950">Drug Intelligence</h2>
            <p className="text-sm text-slate-500">Authorized sources, reviewable signals, and evidence-led correlation.</p>
          </div>
        </div>
        <label className="flex h-10 min-w-56 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-600">
          <KeyRound className="h-4 w-4" />
          <input
            aria-label="Operator key"
            className="min-w-0 flex-1 bg-transparent outline-none"
            type="password"
            value={operatorKey}
            onChange={(event) => setOperatorKey(event.target.value)}
            placeholder="Operator key"
          />
        </label>
      </div>

      {message || queryError ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {message || (queryError instanceof Error ? queryError.message : "Intelligence API is unavailable.")}
        </div>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Summary icon={<Radio />} label="Approved sources" value={summary.approved} />
        <Summary icon={<ClipboardCheck />} label="Awaiting review" value={summary.review} />
        <Summary icon={<BellRing />} label="High-risk signals" value={summary.high} />
        <Summary icon={<Network />} label="Correlations" value={summary.correlations} />
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <form className="border border-slate-200 bg-white p-4 shadow-sm" onSubmit={submitInvestigation}>
          <div className="mb-4 flex items-center gap-2">
            <Fingerprint className="h-5 w-5 text-emerald-700" />
            <h3 className="text-lg font-semibold text-slate-950">Investigation</h3>
          </div>
          <label className="text-sm font-semibold text-slate-700" htmlFor="intel-case-name">Case name</label>
          <input id="intel-case-name" required className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={caseName} onChange={(event) => setCaseName(event.target.value)} />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-slate-700" htmlFor="intel-case-priority">Priority
              <select id="intel-case-priority" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={casePriority} onChange={(event) => setCasePriority(event.target.value as Investigation["priority"])}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700" htmlFor="intel-case-authority">Authorization reference
              <input id="intel-case-authority" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={authorizationReference} onChange={(event) => setAuthorizationReference(event.target.value)} />
            </label>
          </div>
          <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="intel-case-description">Case note</label>
          <textarea id="intel-case-description" className="mt-2 min-h-20 w-full resize-y rounded-md border border-slate-300 bg-slate-50 p-3 text-sm" value={caseDescription} onChange={(event) => setCaseDescription(event.target.value)} />
          <button type="submit" disabled={busy === "investigation"} className="mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50">
            {busy === "investigation" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Create investigation
          </button>
        </form>

        <form className="border border-slate-200 bg-white p-4 shadow-sm" onSubmit={submitSource}>
          <div className="mb-4 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-700" />
            <h3 className="text-lg font-semibold text-slate-950">Intelligence source</h3>
          </div>
          <label className="text-sm font-semibold text-slate-700" htmlFor="intel-source-case">Investigation
            <select id="intel-source-case" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={investigationId ?? ""} onChange={(event) => setSelectedInvestigationId(Number(event.target.value) || null)}>
              <option value="">Unassigned</option>
              {investigations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-slate-700" htmlFor="intel-source-platform">Platform
              <select id="intel-source-platform" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={sourcePlatform} onChange={(event) => setSourcePlatform(event.target.value as "telegram" | "onion")}>
                <option value="telegram">Telegram Bot source</option><option value="onion">Onion crawl source</option>
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700" htmlFor="intel-source-name">Source label
              <input id="intel-source-name" required className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={sourceName} onChange={(event) => setSourceName(event.target.value)} />
            </label>
          </div>
          <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="intel-source-external-id">{sourcePlatform === "telegram" ? "Numeric chat ID" : "Onion URL"}
            <input id="intel-source-external-id" required inputMode={sourcePlatform === "telegram" ? "numeric" : "url"} className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={sourceExternalId} onChange={(event) => setSourceExternalId(event.target.value)} />
          </label>
          <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="intel-source-url">Public reference
            <input id="intel-source-url" type="url" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} />
          </label>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-slate-700" htmlFor="intel-source-approval">Authorization
              <select id="intel-source-approval" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={sourceAuthorization} onChange={(event) => setSourceAuthorization(event.target.value as "pending" | "approved")}>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700" htmlFor="intel-source-cadence">Cadence in minutes
              <input id="intel-source-cadence" min={1} type="number" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={sourceInterval} onChange={(event) => setSourceInterval(Math.max(1, Number(event.target.value)))} />
            </label>
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={sourceEnabled} onChange={(event) => setSourceEnabled(event.target.checked)} /> Enable approved collection
          </label>
          <button type="submit" disabled={busy === "source"} className="mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50">
            {busy === "source" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Register source
          </button>
        </form>
      </div>

      <section className="border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
          <Radio className="h-5 w-5 text-emerald-700" />
          <h3 className="text-lg font-semibold text-slate-950">Source registry</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs uppercase text-slate-500"><tr><th className="px-3 py-2">Source</th><th className="px-3 py-2">Authorization</th><th className="px-3 py-2">Evidence</th><th className="px-3 py-2">Latest activity</th><th className="px-3 py-2"><span className="sr-only">Run source</span></th></tr></thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id} className="border-t border-slate-100">
                  <td className="px-3 py-3"><div className="font-semibold text-slate-900">{source.display_name}</div><div className="font-mono text-xs text-slate-500">{source.platform} · {source.external_id}</div></td>
                  <td className="px-3 py-3"><span className={`inline-flex rounded border px-2 py-1 text-xs font-semibold ${tone(source.authorization_status)}`}>{source.authorization_status}</span></td>
                  <td className="px-3 py-3 text-slate-700">{source.evidence_count}</td>
                  <td className="px-3 py-3 text-slate-600">{when(source.last_collected_at)}</td>
                  <td className="px-3 py-3 text-right"><button type="button" title="Run source" disabled={source.platform !== "telegram" || !source.enabled || source.authorization_status !== "approved" || busy === `source-${source.id}`} onClick={() => runSource(source.id)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-700 disabled:opacity-40"><Play className="h-4 w-4" /></button></td>
                </tr>
              ))}
              {!sources.length ? <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-500">No approved intelligence sources registered.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
            <ClipboardCheck className="h-5 w-5 text-emerald-700" />
            <h3 className="text-lg font-semibold text-slate-950">Triage queue</h3>
          </div>
          <div className="flex flex-col gap-2">
            {signals.map((signal) => (
              <button key={signal.id} type="button" onClick={() => setSelectedSignalId(signal.id)} className={`grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 border p-3 text-left ${selectedSignal?.id === signal.id ? "border-emerald-500 bg-emerald-50" : "border-slate-200 bg-white"}`}>
                <span className={`grid h-9 w-9 place-items-center rounded-full text-sm font-bold ${signal.risk_score >= 70 ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>{signal.risk_score}</span>
                <span className="min-w-0"><span className="block truncate font-semibold text-slate-900">{signal.source_name}</span><span className="block truncate text-xs text-slate-500">{signal.matched_terms.join(" · ") || signal.signal_type}</span></span>
                <span className={`rounded border px-2 py-1 text-xs font-semibold ${tone(signal.review_status)}`}>{signal.review_status}</span>
              </button>
            ))}
            {!signals.length ? <Empty label="No reviewable signals in this investigation." /> : null}
          </div>
        </section>

        <section className="border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
            <BadgeCheck className="h-5 w-5 text-emerald-700" />
            <h3 className="text-lg font-semibold text-slate-950">Analyst decision</h3>
          </div>
          {selectedSignal ? (
            <div className="flex flex-col gap-3">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">{evidence.find((item) => item.id === selectedSignal.evidence)?.content || "Evidence is not available in this filter."}</div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="text-sm font-semibold text-slate-700" htmlFor="intel-review-status">Decision
                  <select id="intel-review-status" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value as DrugSignal["review_status"])}>
                    <option value="triaged">Triaged</option><option value="corroborated">Corroborated</option><option value="false_positive">False positive</option><option value="escalated">Escalated</option><option value="closed">Closed</option>
                  </select>
                </label>
                <label className="text-sm font-semibold text-slate-700" htmlFor="intel-reviewer">Reviewer
                  <input id="intel-reviewer" className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm" value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
                </label>
              </div>
              <label className="text-sm font-semibold text-slate-700" htmlFor="intel-review-note">Review note
                <textarea id="intel-review-note" className="mt-2 min-h-20 w-full resize-y rounded-md border border-slate-300 bg-slate-50 p-3 text-sm" value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
              </label>
              <button type="button" disabled={busy === `signal-${selectedSignal.id}`} onClick={saveReview} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50">{busy === `signal-${selectedSignal.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />} Save decision</button>
            </div>
          ) : <Empty label="Select a signal to record a review decision." />}
        </section>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
            <FileSearch className="h-5 w-5 text-emerald-700" />
            <h3 className="text-lg font-semibold text-slate-950">Evidence ledger</h3>
          </div>
          <div className="flex flex-col gap-3">
            {evidence.slice(0, 6).map((item) => <div key={item.id} className="border-b border-slate-100 pb-3 last:border-0"><div className="flex items-center justify-between gap-3"><span className="font-semibold text-slate-900">{item.source_name}</span><span className="font-mono text-xs text-slate-500">SHA-256 {item.content_hash.slice(0, 12)}</span></div><p className="mt-1 line-clamp-2 text-sm text-slate-600">{item.content || "No text payload"}</p><div className="mt-2 text-xs text-slate-500">v{item.version} · {when(item.occurred_at || item.captured_at)}</div></div>)}
            {!evidence.length ? <Empty label="No evidence has been captured for this investigation." /> : null}
          </div>
        </section>

        <section className="border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3"><Link2 className="h-5 w-5 text-emerald-700" /><h3 className="text-lg font-semibold text-slate-950">Correlation findings</h3><button type="button" title="Refresh correlations" disabled={!investigationId || busy === "correlate"} onClick={runCorrelation} className="ml-auto inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-700 disabled:opacity-40">{busy === "correlate" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Network className="h-4 w-4" />}</button></div>
          <div className="flex flex-col gap-3">
            {correlations.map((finding) => <div key={finding.id} className="border-l-2 border-emerald-500 bg-slate-50 p-3"><div className="flex items-center justify-between gap-2"><h4 className="font-semibold text-slate-900">{finding.title}</h4><span className={`rounded border px-2 py-1 text-xs font-semibold ${tone(finding.severity)}`}>{finding.severity}</span></div><p className="mt-1 text-sm text-slate-600">{finding.description}</p></div>)}
            {!correlations.length ? <Empty label={`No repeated indicators among ${entities.length} captured entities.`} /> : null}
          </div>
        </section>
      </div>
    </div>
  );
}

function Summary({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return <div className="border border-slate-200 bg-white p-3 shadow-sm"><div className="flex items-center gap-2 text-slate-500">{icon}<span className="text-xs font-semibold uppercase">{label}</span></div><div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div></div>;
}

function Empty({ label }: { label: string }) {
  return <div className="border border-dashed border-slate-300 px-3 py-8 text-center text-sm text-slate-500">{label}</div>;
}

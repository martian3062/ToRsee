"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BellRing,
  Clock3,
  GitCompareArrows,
  Loader2,
  Play,
  Plus,
  Radar,
  Radio,
} from "lucide-react";
import { useState, type FormEvent } from "react";

import { useMonitoringStream } from "@/hooks/use-monitoring-stream";
import {
  createAlertRule,
  createMonitoredTarget,
  getAlertEvents,
  getAlertRules,
  getMonitoredTargets,
  getSnapshots,
  runMonitoredTarget,
  updateAlertRule,
  updateMonitoredTarget,
} from "@/lib/api";
import { monitoringKeys } from "@/lib/query-keys";
import type { AlertRule, MonitoredTarget } from "@/lib/types";

const targetKinds: Array<{ value: MonitoredTarget["kind"]; label: string }> = [
  { value: "username", label: "Username re-check" },
  { value: "domain", label: "Domain + OONI" },
  { value: "ooni", label: "OONI poll" },
  { value: "tor_relay", label: "Tor relay monitor" },
  { value: "onion", label: "Onion crawl" },
];

const eventTypes: Array<{ value: AlertRule["event_type"]; label: string }> = [
  { value: "relay_anomaly", label: "Relay anomaly" },
  { value: "censorship", label: "Censorship incident" },
  { value: "keyword_hit", label: "Crawler keyword hit" },
  { value: "change", label: "Snapshot change" },
  { value: "drug_signal", label: "Drug-intelligence signal" },
];

const conditionExamples: Record<AlertRule["event_type"], string> = {
  relay_anomaly: '{"severity":"high","min_score":0.8}',
  censorship: '{"min_failure_rate":0.3}',
  keyword_hit: '{"keyword":"leak","min_count":1}',
  change: '{"source_type":"username"}',
  drug_signal: '{"min_risk_score":70}',
};

function when(value: string | null): string {
  if (!value) return "pending";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function MonitoringPanel() {
  const queryClient = useQueryClient();
  const streamStatus = useMonitoringStream();
  const queryOptions = {
    refetchInterval: 30_000,
  };
  const targetsQuery = useQuery({
    queryKey: monitoringKeys.targets,
    queryFn: getMonitoredTargets,
    ...queryOptions,
  });
  const snapshotsQuery = useQuery({
    queryKey: monitoringKeys.snapshots,
    queryFn: getSnapshots,
    ...queryOptions,
  });
  const rulesQuery = useQuery({
    queryKey: monitoringKeys.rules,
    queryFn: getAlertRules,
    ...queryOptions,
  });
  const eventsQuery = useQuery({
    queryKey: monitoringKeys.events,
    queryFn: getAlertEvents,
    ...queryOptions,
  });
  const targets = targetsQuery.data ?? [];
  const snapshots = snapshotsQuery.data ?? [];
  const rules = rulesQuery.data ?? [];
  const events = eventsQuery.data ?? [];
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const [targetKind, setTargetKind] = useState<MonitoredTarget["kind"]>("username");
  const [targetValue, setTargetValue] = useState("johndoe");
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [keywords, setKeywords] = useState("market,leak,breach");

  const [ruleName, setRuleName] = useState("High-confidence relay anomaly");
  const [eventType, setEventType] = useState<AlertRule["event_type"]>("relay_anomaly");
  const [conditions, setConditions] = useState(conditionExamples.relay_anomaly);
  const [ruleTarget, setRuleTarget] = useState("");
  const [cooldown, setCooldown] = useState(60);

  const queryError = [
    targetsQuery.error,
    snapshotsQuery.error,
    rulesQuery.error,
    eventsQuery.error,
  ].find(Boolean);

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: monitoringKeys.all });
  }

  async function submitTarget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("target");
    setMessage("");
    try {
      await createMonitoredTarget({
        kind: targetKind,
        value: targetValue.trim(),
        interval: intervalMinutes * 60,
        config:
          targetKind === "onion"
            ? { keywords: keywords.split(",").map((item) => item.trim()).filter(Boolean) }
            : {},
      });
      setMessage("Watch target created. Celery Beat will dispatch it when due.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create watch target.");
    } finally {
      setBusy("");
    }
  }

  async function runNow(target: MonitoredTarget) {
    setBusy(`run-${target.id}`);
    setMessage("");
    try {
      await runMonitoredTarget(target.id);
      setMessage(`Dispatched ${target.kind} monitor for ${target.value}.`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not dispatch target.");
    } finally {
      setBusy("");
    }
  }

  async function toggleTarget(target: MonitoredTarget) {
    setBusy(`target-${target.id}`);
    try {
      await updateMonitoredTarget(target.id, { enabled: !target.enabled });
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update target.");
    } finally {
      setBusy("");
    }
  }

  async function submitRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("rule");
    setMessage("");
    try {
      const parsed = JSON.parse(conditions) as Record<string, unknown>;
      await createAlertRule({
        name: ruleName.trim(),
        event_type: eventType,
        conditions: parsed,
        monitored_target: ruleTarget ? Number(ruleTarget) : null,
        cooldown_minutes: cooldown,
      });
      setMessage("Alert rule created and ready to evaluate new events.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Conditions must be a valid JSON object.");
    } finally {
      setBusy("");
    }
  }

  async function toggleRule(rule: AlertRule) {
    setBusy(`rule-${rule.id}`);
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled });
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update rule.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
        <span>30-second polling fallback is active.</span>
        <span
          className={`inline-flex items-center gap-1.5 font-bold uppercase ${
            streamStatus === "live" ? "text-emerald-700" : "text-amber-700"
          }`}
        >
          <Radio className={`h-3.5 w-3.5 ${streamStatus === "live" ? "animate-pulse" : ""}`} />
          {streamStatus === "live" ? "live SSE" : streamStatus}
        </span>
      </div>

      {message || queryError ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {message ||
            (queryError instanceof Error
              ? queryError.message
              : "Monitoring API is unavailable until migrations are applied.")}
        </div>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Summary icon={<Radar />} label="Watch targets" value={targets.length} />
        <Summary icon={<Activity />} label="Active" value={targets.filter((item) => item.enabled).length} />
        <Summary icon={<GitCompareArrows />} label="Changes" value={snapshots.filter((item) => item.changed).length} />
        <Summary icon={<BellRing />} label="Alerts sent" value={events.filter((item) => item.delivered).length} />
      </section>

      <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={submitTarget}>
          <div className="mb-4 flex items-center gap-2">
            <Radar className="h-5 w-5 text-emerald-600" />
            <div>
              <h2 className="text-lg font-semibold">Add continuous watch</h2>
              <p className="text-xs text-slate-500">Beat checks due targets every minute.</p>
            </div>
          </div>
          <label className="text-sm font-semibold text-slate-700" htmlFor="monitor-kind">Watch type</label>
          <select
            id="monitor-kind"
            className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
            value={targetKind}
            onChange={(event) => setTargetKind(event.target.value as MonitoredTarget["kind"])}
          >
            {targetKinds.map((kind) => <option key={kind.value} value={kind.value}>{kind.label}</option>)}
          </select>
          <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="monitor-value">Target</label>
          <input
            id="monitor-value"
            required
            className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
            value={targetValue}
            onChange={(event) => setTargetValue(event.target.value)}
            placeholder={targetKind === "onion" ? "http://example.onion/" : "Target value"}
          />
          <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="monitor-interval">
            Cadence in minutes
          </label>
          <input
            id="monitor-interval"
            required
            min={1}
            type="number"
            className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
            value={intervalMinutes}
            onChange={(event) => setIntervalMinutes(Math.max(1, Number(event.target.value)))}
          />
          {targetKind === "onion" ? (
            <>
              <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="monitor-keywords">
                Watch keywords
              </label>
              <input
                id="monitor-keywords"
                className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
                value={keywords}
                onChange={(event) => setKeywords(event.target.value)}
              />
            </>
          ) : null}
          <button
            className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50"
            disabled={busy === "target"}
            type="submit"
          >
            {busy === "target" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create watch
          </button>
        </form>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock3 className="h-5 w-5 text-emerald-600" />
              <h2 className="text-lg font-semibold">Scheduled targets</h2>
            </div>
            <span className="rounded bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase text-slate-600">
              {targets.filter((target) => target.enabled).length} enabled
            </span>
          </div>
          <div className="space-y-2">
            {targets.length === 0 ? <Empty label="No watch targets yet" /> : null}
            {targets.map((target) => (
              <div key={target.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-800">
                        {target.kind.replace("_", " ")}
                      </span>
                      <span className={`text-[10px] font-bold uppercase ${target.enabled ? "text-emerald-700" : "text-slate-400"}`}>
                        {target.enabled ? "watching" : "paused"}
                      </span>
                    </div>
                    <div className="mt-2 truncate font-mono text-xs font-semibold text-slate-800">{target.value}</div>
                    <div className="mt-1 text-[11px] text-slate-500">
                      every {Math.round(target.interval / 60)}m · last {when(target.last_run)} · next {when(target.next_run)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => toggleTarget(target)}
                      className="h-8 rounded border border-slate-300 bg-white px-3 text-xs font-semibold"
                    >
                      {target.enabled ? "Pause" : "Enable"}
                    </button>
                    <button
                      type="button"
                      disabled={!target.enabled || busy === `run-${target.id}`}
                      onClick={() => runNow(target)}
                      className="inline-flex h-8 items-center gap-1 rounded bg-emerald-700 px-3 text-xs font-semibold text-white disabled:opacity-40"
                    >
                      {busy === `run-${target.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                      Run now
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={submitRule}>
          <div className="mb-4 flex items-center gap-2">
            <BellRing className="h-5 w-5 text-amber-600" />
            <div>
              <h2 className="text-lg font-semibold">Alert rule engine</h2>
              <p className="text-xs text-slate-500">Exact fields plus min_, max_, and _contains operators.</p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs font-semibold text-slate-700">
              Rule name
              <input
                required
                className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
                value={ruleName}
                onChange={(event) => setRuleName(event.target.value)}
              />
            </label>
            <label className="text-xs font-semibold text-slate-700">
              Event
              <select
                className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
                value={eventType}
                onChange={(event) => {
                  const value = event.target.value as AlertRule["event_type"];
                  setEventType(value);
                  setConditions(conditionExamples[value]);
                }}
              >
                {eventTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="text-xs font-semibold text-slate-700">
              Scope
              <select
                className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
                value={ruleTarget}
                onChange={(event) => setRuleTarget(event.target.value)}
              >
                <option value="">All matching targets</option>
                {targets.map((target) => <option key={target.id} value={target.id}>{target.kind}: {target.value}</option>)}
              </select>
            </label>
            <label className="text-xs font-semibold text-slate-700">
              Cooldown minutes
              <input
                min={0}
                type="number"
                className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm"
                value={cooldown}
                onChange={(event) => setCooldown(Math.max(0, Number(event.target.value)))}
              />
            </label>
          </div>
          <label className="mt-3 block text-xs font-semibold text-slate-700" htmlFor="rule-conditions">
            Conditions JSON
          </label>
          <textarea
            id="rule-conditions"
            className="mt-1 min-h-20 w-full rounded-md border border-slate-300 bg-slate-950 p-3 font-mono text-xs text-emerald-200"
            value={conditions}
            onChange={(event) => setConditions(event.target.value)}
          />
          <button
            className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50"
            disabled={busy === "rule"}
            type="submit"
          >
            {busy === "rule" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create alert rule
          </button>
        </form>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Rules</h2>
          <div className="space-y-2">
            {rules.length === 0 ? <Empty label="Built-in critical alerts are active; add a custom filter here" /> : null}
            {rules.map((rule) => (
              <div key={rule.id} className="flex items-start justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                <div>
                  <div className="font-semibold text-slate-900">{rule.name}</div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    {rule.event_type.replace("_", " ")} · cooldown {rule.cooldown_minutes}m
                  </div>
                  <code className="mt-2 block break-all text-[10px] text-emerald-800">
                    {JSON.stringify(rule.conditions)}
                  </code>
                </div>
                <button
                  type="button"
                  onClick={() => toggleRule(rule)}
                  className={`rounded px-2 py-1 text-[10px] font-bold uppercase ${
                    rule.enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {rule.enabled ? "enabled" : "paused"}
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <GitCompareArrows className="h-5 w-5 text-emerald-600" />
            <h2 className="text-lg font-semibold">Change snapshots</h2>
          </div>
          <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
            {snapshots.length === 0 ? <Empty label="Snapshots appear after username checks and crawls" /> : null}
            {snapshots.slice(0, 30).map((snapshot) => (
              <div key={snapshot.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-xs font-semibold">{snapshot.target}</span>
                  <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                    snapshot.changed ? "bg-amber-100 text-amber-900" : "bg-slate-200 text-slate-600"
                  }`}>
                    {snapshot.changed ? "changed" : "baseline"}
                  </span>
                </div>
                <div className="mt-1 text-[10px] uppercase text-slate-500">{snapshot.source_type} · {when(snapshot.created_at)}</div>
                {snapshot.changed ? (
                  <code className="mt-2 block break-all text-[10px] text-slate-700">{JSON.stringify(snapshot.diff)}</code>
                ) : null}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <BellRing className="h-5 w-5 text-amber-600" />
            <h2 className="text-lg font-semibold">Alert delivery log</h2>
          </div>
          <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
            {events.length === 0 ? <Empty label="No alert events yet" /> : null}
            {events.slice(0, 30).map((event) => (
              <div key={event.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-slate-900">{event.title}</div>
                  <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                    event.severity === "high" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"
                  }`}>
                    {event.severity}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-600">{event.message}</p>
                <div className="mt-2 text-[10px] uppercase text-slate-500">
                  {event.delivered ? "Telegram delivered" : "delivery pending"} · {event.rule_name || "built-in rule"} · {when(event.created_at)}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Summary({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</div>
        <div className="mt-1 text-2xl font-bold text-slate-900">{value}</div>
      </div>
      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">{icon}</div>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-6 text-center text-sm text-slate-500">
      {label}
    </div>
  );
}

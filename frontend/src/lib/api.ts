import type {
  HealthPayload,
  IngestionJob,
  SearchMatch,
  OSINTScan,
  CensorshipIncident,
  RelayAnomaly,
  DarkWebCrawl,
  MonitoredTarget,
  Snapshot,
  AlertRule,
  AlertEvent,
  Investigation,
  IntelligenceSource,
  EvidenceItem,
  DrugSignal,
  IntelligenceEntity,
  CorrelationFinding,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

let intelligenceOperatorKey = "";

export function setIntelligenceOperatorKey(value: string): void {
  intelligenceOperatorKey = value.trim();
}

async function intelligenceRequest<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(`/intel${path}`, {
    ...init,
    headers: {
      ...(intelligenceOperatorKey ? { "X-ToRsy-Operator-Key": intelligenceOperatorKey } : {}),
      ...(init?.headers ?? {}),
    },
  });
}

export async function getHealth(): Promise<HealthPayload> {
  return request<HealthPayload>("/health");
}

export async function getJobs(): Promise<IngestionJob[]> {
  return request<IngestionJob[]>("/jobs/");
}

export async function ingestUrls(payload: {
  urls: string[];
  provider_preference: string[];
  tags: string[];
  notify: boolean;
}) {
  return request<IngestionJob>("/jobs/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function searchDocuments(query: string): Promise<{ local_matches: SearchMatch[] }> {
  return request<{ local_matches: SearchMatch[] }>("/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: 8 }),
  });
}

export async function getOSINTScans(): Promise<OSINTScan[]> {
  return request<OSINTScan[]>("/osint/scan/");
}

export async function getOSINTScan(id: number): Promise<OSINTScan> {
  return request<OSINTScan>(`/osint/scan/${id}/`);
}

export async function createOSINTScan(payload: { target: string; scan_type: string }): Promise<OSINTScan> {
  return request<OSINTScan>("/osint/scan/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCensorshipIncidents(): Promise<CensorshipIncident[]> {
  return request<CensorshipIncident[]>("/osint/censorship/");
}

export async function getRelayAnomalies(): Promise<RelayAnomaly[]> {
  return request<RelayAnomaly[]>("/osint/anomalies/");
}

export async function runRelayMonitor(
  search: string
): Promise<{ summary: { observations: number; anomalies: number }; anomalies: RelayAnomaly[] }> {
  return request("/osint/anomalies/", {
    method: "POST",
    body: JSON.stringify({ search }),
  });
}

export async function getCrawls(): Promise<DarkWebCrawl[]> {
  return request<DarkWebCrawl[]>("/osint/crawl/");
}

export async function createCrawl(payload: {
  url: string;
  keywords: string;
}): Promise<DarkWebCrawl> {
  return request<DarkWebCrawl>("/osint/crawl/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMonitoredTargets(): Promise<MonitoredTarget[]> {
  return request<MonitoredTarget[]>("/osint/monitors/");
}

export async function createMonitoredTarget(payload: {
  kind: MonitoredTarget["kind"];
  value: string;
  interval: number;
  config: Record<string, unknown>;
}): Promise<MonitoredTarget> {
  return request<MonitoredTarget>("/osint/monitors/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateMonitoredTarget(
  id: number,
  payload: Partial<Pick<MonitoredTarget, "enabled" | "interval" | "config">>
): Promise<MonitoredTarget> {
  return request<MonitoredTarget>(`/osint/monitors/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function runMonitoredTarget(
  id: number
): Promise<{ target: MonitoredTarget; dispatch: Record<string, unknown> }> {
  return request(`/osint/monitors/${id}/run/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getSnapshots(): Promise<Snapshot[]> {
  return request<Snapshot[]>("/osint/snapshots/");
}

export async function getAlertRules(): Promise<AlertRule[]> {
  return request<AlertRule[]>("/osint/alert-rules/");
}

export async function createAlertRule(payload: {
  name: string;
  event_type: AlertRule["event_type"];
  conditions: Record<string, unknown>;
  monitored_target: number | null;
  cooldown_minutes: number;
}): Promise<AlertRule> {
  return request<AlertRule>("/osint/alert-rules/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAlertRule(
  id: number,
  payload: Partial<Pick<AlertRule, "enabled" | "conditions" | "cooldown_minutes">>
): Promise<AlertRule> {
  return request<AlertRule>(`/osint/alert-rules/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getAlertEvents(): Promise<AlertEvent[]> {
  return request<AlertEvent[]>("/osint/alert-events/");
}

export async function getInvestigations(): Promise<Investigation[]> {
  return intelligenceRequest<Investigation[]>("/investigations/");
}

export async function createInvestigation(payload: Pick<Investigation, "name" | "description" | "priority" | "authorization_reference">): Promise<Investigation> {
  return intelligenceRequest<Investigation>("/investigations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getIntelligenceSources(): Promise<IntelligenceSource[]> {
  return intelligenceRequest<IntelligenceSource[]>("/sources/");
}

export async function createIntelligenceSource(payload: {
  investigation: number | null;
  platform: IntelligenceSource["platform"];
  external_id: string;
  display_name: string;
  public_url: string;
  collection_mode: IntelligenceSource["collection_mode"];
  authorization_status: IntelligenceSource["authorization_status"];
  enabled: boolean;
  interval: number;
}): Promise<IntelligenceSource> {
  return intelligenceRequest<IntelligenceSource>("/sources/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runIntelligenceSource(id: number): Promise<{ source: IntelligenceSource; task_id: string }> {
  return intelligenceRequest<{ source: IntelligenceSource; task_id: string }>(`/sources/${id}/run/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getEvidenceItems(investigation?: number): Promise<EvidenceItem[]> {
  const query = investigation ? `?investigation=${investigation}` : "";
  return intelligenceRequest<EvidenceItem[]>(`/evidence/${query}`);
}

export async function getDrugSignals(investigation?: number): Promise<DrugSignal[]> {
  const query = investigation ? `?investigation=${investigation}` : "";
  return intelligenceRequest<DrugSignal[]>(`/signals/${query}`);
}

export async function reviewDrugSignal(
  id: number,
  payload: { status: DrugSignal["review_status"]; reviewer: string; note: string }
): Promise<DrugSignal> {
  return intelligenceRequest<DrugSignal>(`/signals/${id}/review/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getIntelligenceEntities(): Promise<IntelligenceEntity[]> {
  return intelligenceRequest<IntelligenceEntity[]>("/entities/");
}

export async function getCorrelationFindings(investigation?: number): Promise<CorrelationFinding[]> {
  const query = investigation ? `?investigation=${investigation}` : "";
  return intelligenceRequest<CorrelationFinding[]>(`/correlations/${query}`);
}

export async function correlateInvestigation(id: number): Promise<CorrelationFinding[]> {
  return intelligenceRequest<CorrelationFinding[]>(`/investigations/${id}/correlate/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

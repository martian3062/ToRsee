import type {
  HealthPayload,
  IngestionJob,
  SearchMatch,
  OSINTScan,
  CensorshipIncident,
  RelayAnomaly,
  DarkWebCrawl,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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


export type ProviderState = {
  key: string;
  label: string;
  role: string;
  status: "configured" | "missing_key" | "disabled" | "mocked";
  configured: boolean;
  mock_mode: boolean;
};

export type DocumentRecord = {
  id: number;
  url: string;
  title: string;
  content_markdown: string;
  metadata: Record<string, unknown>;
  embedding_id: string;
  created_at: string;
};

export type JobTarget = {
  id: number;
  url: string;
  status: "queued" | "fetched" | "failed";
  fetched_with: string;
  document: DocumentRecord | null;
  error: string;
  created_at: string;
  updated_at: string;
};

export type IngestionJob = {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  provider_preference: string[];
  tags: string[];
  notification_settings: Record<string, unknown>;
  error: string;
  cost_metadata: Record<string, unknown>;
  result_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  targets: JobTarget[];
};

export type HealthPayload = {
  status: string;
  checks: Record<string, string>;
  providers: ProviderState[];
};

export type SearchMatch = {
  id: number;
  title: string;
  url: string;
  snippet: string;
  embedding_id: string;
  source: string;
};

export type OSINTScan = {
  id: number;
  target: string;
  scan_type: "username" | "domain" | "metadata" | "tor_relay";
  status: "queued" | "running" | "completed" | "failed";
  error: string;
  results: Record<string, any>;
  created_at: string;
  updated_at: string;
};

export type CensorshipIncident = {
  id: number;
  country_code: string;
  asn: string;
  target_domain: string;
  anomaly_type: string;
  measurement_count: number;
  failure_rate: number;
  reported_at: string;
};

export type RelayAnomaly = {
  id: number;
  fingerprint: string;
  nickname: string;
  country_code: string;
  country_name: string;
  as_number: string;
  latitude: number | null;
  longitude: number | null;
  metric: string;
  anomaly_type: string;
  score: number;
  severity: "low" | "medium" | "high";
  detector: string;
  detail: Record<string, any>;
  detected_at: string;
};

export type DarkWebCrawl = {
  id: number;
  url: string;
  keywords: string;
  status: "queued" | "running" | "completed" | "failed";
  routed_via_tor: boolean;
  is_onion: boolean;
  error: string;
  results: Record<string, any>;
  created_at: string;
  updated_at: string;
};


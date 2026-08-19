import type {
  AlertEventSeverityEnum,
  EventTypeEnum,
  JobTargetStatusEnum,
  MonitoredTargetKindEnum,
  ProcessingStatusEnum,
  ScanTypeEnum,
  SourceTypeEnum,
} from "./openapi/types.gen";

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
  status: JobTargetStatusEnum;
  fetched_with: string;
  document: DocumentRecord | null;
  error: string;
  created_at: string;
  updated_at: string;
};

export type IngestionJob = {
  id: string;
  status: ProcessingStatusEnum;
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
  database: {
    engine: "sqlite" | "postgresql" | string;
    extensions: string[];
  };
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
  scan_type: ScanTypeEnum;
  status: ProcessingStatusEnum;
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
  status: ProcessingStatusEnum;
  routed_via_tor: boolean;
  is_onion: boolean;
  error: string;
  results: Record<string, any>;
  created_at: string;
  updated_at: string;
};

export type MonitoredTarget = {
  id: number;
  kind: MonitoredTargetKindEnum;
  value: string;
  interval: number;
  enabled: boolean;
  config: Record<string, unknown>;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
  updated_at: string;
};

export type Snapshot = {
  id: number;
  source_type: SourceTypeEnum;
  target: string;
  content_hash: string;
  changed: boolean;
  diff: Record<string, unknown>;
  monitored_target: number | null;
  osint_scan: number | null;
  darkweb_crawl: number | null;
  previous: number | null;
  created_at: string;
};

export type AlertRule = {
  id: number;
  name: string;
  event_type: EventTypeEnum;
  conditions: Record<string, unknown>;
  enabled: boolean;
  monitored_target: number | null;
  cooldown_minutes: number;
  last_triggered: string | null;
  created_at: string;
  updated_at: string;
};

export type AlertEvent = {
  id: number;
  rule: number | null;
  rule_name: string;
  monitored_target: number | null;
  event_type: AlertRule["event_type"];
  severity: AlertEventSeverityEnum;
  title: string;
  message: string;
  payload: Record<string, unknown>;
  delivered: boolean;
  created_at: string;
};

export type Investigation = {
  id: number;
  name: string;
  description: string;
  status: "open" | "paused" | "closed";
  priority: "low" | "medium" | "high";
  authorization_reference: string;
  source_count: number;
  signal_count: number;
  created_at: string;
  updated_at: string;
};

export type IntelligenceSource = {
  id: number;
  investigation: number | null;
  platform: "telegram" | "onion" | "manual";
  external_id: string;
  display_name: string;
  public_url: string;
  collection_mode: "bot_webhook" | "approved_public" | "manual";
  authorization_status: "pending" | "approved" | "suspended";
  enabled: boolean;
  interval: number;
  latest_cursor: string;
  last_collected_at: string | null;
  next_run: string | null;
  evidence_count: number;
  created_at: string;
  updated_at: string;
};

export type EvidenceItem = {
  id: number;
  source: number;
  source_name: string;
  investigation: number | null;
  kind: "telegram_message" | "onion_crawl" | "manual";
  external_id: string;
  version: number;
  is_latest: boolean;
  is_deleted: boolean;
  author_alias: string;
  reply_to_external_id: string;
  forwarded_from: string;
  public_url: string;
  content: string;
  normalized_content: string;
  content_hash: string;
  occurred_at: string | null;
  captured_at: string;
  signal_count: number;
};

export type DrugSignal = {
  id: number;
  evidence: number;
  evidence_external_id: string;
  source_name: string;
  investigation: number | null;
  signal_type: "illicit_sale" | "controlled_substance";
  risk_score: number;
  matched_terms: string[];
  evidence_spans: Array<{ category: string; term: string; start: number; end: number }>;
  rule_version: string;
  review_status: "new" | "triaged" | "corroborated" | "false_positive" | "escalated" | "closed";
  reviewed_by: string;
  review_note: string;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type IntelligenceEntity = {
  id: number;
  kind: string;
  value: string;
  normalized_value: string;
  display_name: string;
  evidence_count: number;
  created_at: string;
  updated_at: string;
};

export type CorrelationFinding = {
  id: number;
  investigation: number;
  title: string;
  description: string;
  severity: "low" | "medium" | "high";
  supporting_evidence_ids: number[];
  entity_ids: number[];
  created_at: string;
  updated_at: string;
};

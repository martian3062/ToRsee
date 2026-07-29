import type { HealthPayload, IngestionJob } from "./types";

export const fallbackHealth: HealthPayload = {
  status: "offline",
  checks: { database: "waiting", redis: "waiting" },
  database: { engine: "sqlite", extensions: [] },
  providers: [
    { key: "firecrawl", label: "Firecrawl", role: "primary scraping", status: "mocked", configured: false, mock_mode: true },
    { key: "groq", label: "Groq", role: "summaries", status: "mocked", configured: false, mock_mode: true },
    { key: "pinecone", label: "Pinecone", role: "vector search", status: "mocked", configured: false, mock_mode: true },
    { key: "telegram", label: "Telegram", role: "alerts", status: "mocked", configured: false, mock_mode: true },
  ],
};

export const fallbackJobs: IngestionJob[] = [];

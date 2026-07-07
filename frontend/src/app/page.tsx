"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  Bell,
  Database,
  FileSearch,
  Link2,
  Loader2,
  RefreshCcw,
  Search,
  Send,
  Server,
  Sparkles,
  ShieldAlert,
  UserCheck,
  Globe,
  Cpu,
  MapPin,
  CheckCircle2,
  XCircle,
  Network
} from "lucide-react";
import {
  getHealth,
  getJobs,
  ingestUrls,
  searchDocuments,
  getOSINTScans,
  createOSINTScan,
  getCensorshipIncidents,
  getRelayAnomalies,
  runRelayMonitor,
  getCrawls,
  createCrawl
} from "@/lib/api";
import { fallbackHealth, fallbackJobs } from "@/lib/demo";
import type {
  DocumentRecord,
  HealthPayload,
  IngestionJob,
  SearchMatch,
  OSINTScan,
  CensorshipIncident,
  RelayAnomaly,
  DarkWebCrawl
} from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { FootprintGraph } from "@/components/footprint-graph";
import { RelayMap } from "@/components/relay-map";

const providerOptions = ["firecrawl", "zenrows", "bright_data", "tinyfish", "direct"];
const scanTypeOptions = [
  { value: "username", label: "Username Footprint" },
  { value: "domain", label: "Domain Attack Surface" },
  { value: "metadata", label: "Document Metadata Auditor" },
  { value: "tor_relay", label: "Tor Relay consensus" }
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<"ingest" | "osint" | "network" | "crawler" | "censorship">("ingest");
  const [health, setHealth] = useState<HealthPayload>(fallbackHealth);
  const [jobs, setJobs] = useState<IngestionJob[]>(fallbackJobs);
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(null);
  
  // Ingest form
  const [urls, setUrls] = useState("https://example.com");
  const [tags, setTags] = useState("demo,research");
  const [providers, setProviders] = useState<string[]>(["firecrawl", "zenrows"]);
  const [notify, setNotify] = useState(true);
  
  // Search
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  
  // OSINT form
  const [osintScans, setOsintScans] = useState<OSINTScan[]>([]);
  const [selectedScan, setSelectedScan] = useState<OSINTScan | null>(null);
  const [osintTarget, setOsintTarget] = useState("johndoe");
  const [osintType, setOsintType] = useState<"username" | "domain" | "metadata" | "tor_relay">("username");
  
  // Censorship OONI Data
  const [incidents, setIncidents] = useState<CensorshipIncident[]>([]);

  // Relay anomalies (PyOD)
  const [anomalies, setAnomalies] = useState<RelayAnomaly[]>([]);
  const [anomalySearch, setAnomalySearch] = useState("exit");

  // Dark web crawler
  const [crawls, setCrawls] = useState<DarkWebCrawl[]>([]);
  const [selectedCrawl, setSelectedCrawl] = useState<DarkWebCrawl | null>(null);
  const [crawlUrl, setCrawlUrl] = useState("http://exampleforum7g2z.onion/");
  const [crawlKeywords, setCrawlKeywords] = useState("market,leak,breach");

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function refresh() {
    try {
      const [nextHealth, nextJobs, nextScans, nextIncidents, nextAnomalies, nextCrawls] = await Promise.all([
        getHealth(),
        getJobs(),
        getOSINTScans().catch(() => [] as OSINTScan[]),
        getCensorshipIncidents().catch(() => [] as CensorshipIncident[]),
        getRelayAnomalies().catch(() => [] as RelayAnomaly[]),
        getCrawls().catch(() => [] as DarkWebCrawl[])
      ]);

      setHealth(nextHealth);
      setJobs(nextJobs);
      setOsintScans(nextScans);
      setIncidents(nextIncidents);
      setAnomalies(nextAnomalies);
      setCrawls(nextCrawls);
      if (nextCrawls.length > 0) {
        setSelectedCrawl((current) => current ?? nextCrawls[0]);
      }
      
      const firstDocument = nextJobs.flatMap((job) => job.targets).find((target) => target.document)?.document ?? null;
      setSelectedDocument((current) => current ?? firstDocument);
      
      if (nextScans.length > 0) {
        setSelectedScan((current) => current ?? nextScans[0]);
      }
      setMessage("");
    } catch (error) {
      setMessage("Backend offline or not migrated yet.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const metrics = useMemo(() => {
    const targets = jobs.flatMap((job) => job.targets);
    return {
      jobs: jobs.length,
      documents: targets.filter((target) => target.document).length,
      providers: health.providers.filter((provider) => provider.configured || provider.status === "mocked").length,
      alerts: health.providers.find((provider) => provider.key === "telegram")?.status ?? "mocked",
      scans: osintScans.length,
      anomalies: anomalies.length || incidents.length
    };
  }, [health.providers, jobs, osintScans, incidents, anomalies]);

  async function submitIngest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await ingestUrls({
        urls: urls
          .split(/\r?\n|,/)
          .map((url) => url.trim())
          .filter(Boolean),
        provider_preference: providers,
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        notify,
      });
      setMessage("Ingestion completed.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Ingestion failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await searchDocuments(query);
      setMatches(result.local_matches ?? []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitOSINTScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const scan = await createOSINTScan({
        target: osintTarget,
        scan_type: osintType
      });
      setSelectedScan(scan);
      setMessage(`OSINT ${osintType} scan completed successfully.`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "OSINT scan trigger failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitRelayMonitor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const res = await runRelayMonitor(anomalySearch);
      setAnomalies(res.anomalies);
      setMessage(
        `Monitored ${res.summary.observations} relay observations · ${res.summary.anomalies} anomalies flagged by PyOD.`
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Relay monitor failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitCrawl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const crawl = await createCrawl({ url: crawlUrl, keywords: crawlKeywords });
      setSelectedCrawl(crawl);
      setMessage(`Crawl ${crawl.status}${crawl.routed_via_tor ? " (routed via Tor)" : ""}.`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Crawl failed.");
    } finally {
      setBusy(false);
    }
  }

  function toggleProvider(provider: string) {
    setProviders((current) =>
      current.includes(provider) ? current.filter((item) => item !== provider) : [...current, provider],
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8 bg-slate-50 text-slate-800">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-normal text-slate-900 flex items-center gap-2">
            <Network className="h-6 w-6 text-emerald-600 animate-pulse" />
            ToRsy
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-600">
            <span className="inline-flex items-center gap-1"><Server className="h-4 w-4 text-emerald-500" /> {health.status}</span>
            <span className="inline-flex items-center gap-1"><Database className="h-4 w-4 text-emerald-500" /> DB: {health.checks.database}</span>
            <span className="inline-flex items-center gap-1"><Bell className="h-4 w-4 text-amber-500" /> {metrics.alerts.replace("_", " ")}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold shadow-sm hover:bg-slate-50"
            onClick={refresh}
            type="button"
            title="Refresh Data"
          >
            <RefreshCcw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </header>

      {message ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 transition-all duration-300">
          {message}
        </div>
      ) : null}

      <section className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
        <Metric icon={<Activity />} label="Ingest Jobs" value={metrics.jobs} />
        <Metric icon={<FileSearch />} label="Indexed Docs" value={metrics.documents} />
        <Metric icon={<Cpu />} label="OSINT Scans" value={metrics.scans} />
        <Metric icon={<ShieldAlert />} label="Network Anomalies" value={metrics.anomalies} />
        <Metric icon={<Sparkles />} label="Providers" value={metrics.providers} />
        <Metric icon={<Bell />} label="Telegram Status" value={metrics.alerts.replace("_", " ")} />
      </section>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab("ingest")}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
              activeTab === "ingest"
                ? "border-emerald-600 text-emerald-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Ingest & Search
          </button>
          <button
            onClick={() => setActiveTab("osint")}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
              activeTab === "osint"
                ? "border-emerald-600 text-emerald-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            OSINT Scanner
          </button>
          <button
            onClick={() => setActiveTab("network")}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
              activeTab === "network"
                ? "border-emerald-600 text-emerald-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Relay Anomalies (PyOD)
          </button>
          <button
            onClick={() => setActiveTab("crawler")}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
              activeTab === "crawler"
                ? "border-emerald-600 text-emerald-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Dark Web Crawler
          </button>
          <button
            onClick={() => setActiveTab("censorship")}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
              activeTab === "censorship"
                ? "border-emerald-600 text-emerald-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Censorship Cockpit
          </button>
        </nav>
      </div>

      {/* Tab Contents */}
      {activeTab === "ingest" && (
        <div className="flex flex-col gap-5">
          <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
            <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={submitIngest}>
              <div className="mb-4 flex items-center gap-2">
                <Link2 className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">New Web Ingestion</h2>
              </div>
              <label className="text-sm font-semibold text-slate-700" htmlFor="urls">URLs (comma or line separated)</label>
              <textarea
                id="urls"
                className="mt-2 min-h-28 w-full resize-y rounded-md border border-slate-300 bg-slate-50 p-3 text-sm outline-none focus:border-emerald-600 transition-colors"
                value={urls}
                onChange={(event) => setUrls(event.target.value)}
              />
              <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="tags">Tags</label>
              <input
                id="tags"
                className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600 transition-colors"
                value={tags}
                onChange={(event) => setTags(event.target.value)}
              />
              <div className="mt-4">
                <span className="block text-sm font-semibold text-slate-700 mb-2">Provider Preference</span>
                <div className="flex flex-wrap gap-2">
                  {providerOptions.map((provider) => (
                    <button
                      key={provider}
                      type="button"
                      onClick={() => toggleProvider(provider)}
                      className={`rounded-md border px-3 py-2 text-sm font-semibold transition-all ${
                        providers.includes(provider)
                          ? "border-emerald-600 bg-emerald-50 text-emerald-800"
                          : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      {provider.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
                <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                  <input
                    checked={notify}
                    onChange={(event) => setNotify(event.target.checked)}
                    type="checkbox"
                    className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  Telegram alerts
                </label>
                <button
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
                  disabled={busy}
                  type="submit"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Run Ingestion
                </button>
              </div>
            </form>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">System Providers</h2>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 max-h-[360px] overflow-y-auto">
                {health.providers.map((provider) => (
                  <div key={provider.key} className="rounded-md border border-slate-200 p-3 bg-slate-50">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold text-slate-900">{provider.label}</div>
                        <div className="mt-1 text-xs text-slate-600">{provider.role}</div>
                      </div>
                      <StatusBadge status={provider.status} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Web Jobs Log</h2>
              </div>
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {jobs.length === 0 ? <Empty label="No ingestion jobs yet" /> : null}
                {jobs.map((job) => (
                  <div key={job.id} className="rounded-md border border-slate-200 p-3 hover:border-slate-300 bg-slate-50 transition-colors">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/60 pb-2 mb-2">
                      <div className="min-w-0 text-xs font-mono font-bold text-slate-800 truncate">{job.id}</div>
                      <StatusBadge status={job.status} />
                    </div>
                    <div className="space-y-2">
                      {job.targets.map((target) => (
                        <button
                          key={target.id}
                          className="flex w-full items-center justify-between gap-3 rounded-md border border-slate-200 bg-white px-3 py-2 text-left text-xs hover:border-emerald-600 hover:shadow-sm transition-all"
                          onClick={() => setSelectedDocument(target.document)}
                          type="button"
                        >
                          <span className="min-w-0 truncate text-slate-700 font-semibold">{target.url}</span>
                          <span className="flex shrink-0 items-center gap-2">
                            <span className="text-[10px] text-slate-500 font-mono">{target.fetched_with || "queued"}</span>
                            <StatusBadge status={target.status} />
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Search className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Semantic Search</h2>
              </div>
              <form className="flex gap-2 mb-3" onSubmit={submitSearch}>
                <input
                  className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600 transition-colors"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Ask a question about ingested pages..."
                />
                <button
                  className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-sm"
                  type="submit"
                  title="Search"
                >
                  <Search className="h-4 w-4" />
                </button>
              </form>
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {matches.map((match) => (
                  <button
                    key={match.id}
                    type="button"
                    className="w-full rounded-md border border-slate-200 p-3 text-left bg-slate-50 hover:border-emerald-600 hover:shadow-sm transition-all"
                    onClick={() => {
                      const document = jobs.flatMap((job) => job.targets).find((target) => target.document?.id === match.id)?.document ?? null;
                      setSelectedDocument(document);
                    }}
                  >
                    <div className="font-semibold text-sm text-slate-850 truncate">{match.title || match.url}</div>
                    <div className="mt-1 line-clamp-2 text-xs text-slate-650">{match.snippet}</div>
                  </button>
                ))}
                {matches.length === 0 ? <Empty label="No query matches loaded yet" /> : null}
              </div>
            </section>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-2">
              <FileSearch className="h-5 w-5 text-emerald-600" />
              <h2 className="text-lg font-semibold">Document Viewer & AI Insights</h2>
            </div>
            {selectedDocument ? (
              <div className="grid gap-4 lg:grid-cols-[0.35fr_0.65fr]">
                <div className="rounded-md border border-slate-200 bg-slate-50 p-4 text-xs space-y-3">
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500">Document Title</span>
                    <span className="font-semibold text-slate-900 text-sm">{selectedDocument.title}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500">Source URL</span>
                    <a href={selectedDocument.url} target="_blank" rel="noreferrer" className="break-all text-emerald-700 hover:underline">{selectedDocument.url}</a>
                  </div>
                  <div className="border-t border-slate-200 pt-2">
                    <span className="block text-[10px] uppercase font-bold text-slate-500">Vector Embeddings ID</span>
                    <span className="font-mono text-slate-600 font-semibold">{selectedDocument.embedding_id || "Pending vector index..."}</span>
                  </div>
                  {selectedDocument.metadata && Object.keys(selectedDocument.metadata).length > 0 && (
                    <div className="border-t border-slate-200 pt-2">
                      <span className="block text-[10px] uppercase font-bold text-slate-500 mb-1">Metadata Attributes</span>
                      <pre className="max-h-40 overflow-auto whitespace-pre bg-white border border-slate-200 p-2 rounded text-[10px]">
                        {JSON.stringify(selectedDocument.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
                <div className="flex flex-col border border-slate-200 rounded-md overflow-hidden shadow-inner">
                  <div className="bg-slate-900 text-slate-300 text-xs px-3 py-2 font-mono flex items-center justify-between">
                    <span>Parsed Content Markdown</span>
                    <span className="bg-emerald-800 text-emerald-100 font-bold px-1.5 py-0.5 rounded text-[10px]">RENDERED</span>
                  </div>
                  <pre className="max-h-[380px] overflow-auto whitespace-pre-wrap bg-slate-950 p-4 text-xs text-slate-100 font-mono leading-relaxed">
                    {selectedDocument.content_markdown}
                  </pre>
                </div>
              </div>
            ) : (
              <Empty label="Select an ingested target above to inspect the document markdown" />
            )}
          </section>
        </div>
      )}

      {activeTab === "osint" && (
        <div className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="flex flex-col gap-5">
            <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={submitOSINTScan}>
              <div className="mb-4 flex items-center gap-2">
                <Cpu className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Trigger OSINT Target Scan</h2>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm font-semibold text-slate-700" htmlFor="osintType">Scan Type</label>
                  <select
                    id="osintType"
                    className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600"
                    value={osintType}
                    onChange={(e) => setOsintType(e.target.value as any)}
                  >
                    {scanTypeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-700" htmlFor="osintTarget">Target Value</label>
                  <input
                    id="osintTarget"
                    type="text"
                    className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600 transition-colors"
                    value={osintTarget}
                    onChange={(e) => setOsintTarget(e.target.value)}
                    placeholder={
                      osintType === "username" ? "e.g., torvalds" :
                      osintType === "domain" ? "e.g., duckduckgo.com" :
                      osintType === "metadata" ? "e.g., https://example.com/leak.jpg" :
                      "e.g., exitNode1"
                    }
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end border-t border-slate-100 pt-3">
                <button
                  type="submit"
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 transition-colors shadow-sm disabled:opacity-50"
                  disabled={busy}
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Execute Scan
                </button>
              </div>
            </form>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm flex-1">
              <div className="mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Recent Footprints & Scans</h2>
              </div>
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {osintScans.length === 0 ? <Empty label="No scans performed yet" /> : null}
                {osintScans.map((scan) => (
                  <button
                    key={scan.id}
                    onClick={() => setSelectedScan(scan)}
                    className={`w-full p-3 rounded-md border text-left flex items-center justify-between gap-3 transition-all ${
                      selectedScan?.id === scan.id
                        ? "border-emerald-600 bg-emerald-50/55 shadow-sm"
                        : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-sm text-slate-800 flex items-center gap-1.5">
                        <span className="capitalize text-xs px-2 py-0.5 rounded bg-slate-200 font-bold text-slate-650">{scan.scan_type.replace("_", " ")}</span>
                        {scan.target}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1 font-mono">{new Date(scan.created_at).toLocaleString()}</div>
                    </div>
                    <StatusBadge status={scan.status} />
                  </button>
                ))}
              </div>
            </section>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm flex flex-col min-h-[460px]">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-150 pb-2">
              <UserCheck className="h-5 w-5 text-emerald-600" />
              <h2 className="text-lg font-semibold">Scan Result Analysis</h2>
            </div>
            {selectedScan ? (
              <div className="flex-1 flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 border border-slate-200 rounded p-3">
                  <div>
                    <span className="block uppercase text-[9px] font-bold text-slate-500">Target</span>
                    <span className="font-semibold text-slate-850">{selectedScan.target}</span>
                  </div>
                  <div>
                    <span className="block uppercase text-[9px] font-bold text-slate-500">Scan Type</span>
                    <span className="font-semibold text-slate-850 capitalize">{selectedScan.scan_type.replace("_", " ")}</span>
                  </div>
                  <div>
                    <span className="block uppercase text-[9px] font-bold text-slate-500">Status</span>
                    <StatusBadge status={selectedScan.status} />
                  </div>
                  <div>
                    <span className="block uppercase text-[9px] font-bold text-slate-500">Completed At</span>
                    <span className="font-semibold text-slate-850 font-mono text-[10px]">{new Date(selectedScan.updated_at).toLocaleTimeString()}</span>
                  </div>
                </div>

                {selectedScan.status === "failed" && (
                  <div className="p-3 border border-red-200 bg-red-50 text-red-800 rounded text-xs font-semibold">
                    Error message: {selectedScan.error}
                  </div>
                )}

                {selectedScan.status === "completed" && (
                  <div className="flex-1 flex flex-col">
                    {selectedScan.scan_type === "username" && (
                      <div className="flex-1 flex flex-col gap-4">
                        <span className="text-xs font-bold text-slate-700">Digital Footprint Mapping:</span>
                        
                        {/* Reagraph WebGL footprint graph */}
                        <FootprintGraph
                          username={selectedScan.target}
                          details={selectedScan.results.scan_details ?? []}
                        />
                        {selectedScan.results.sites_checked ? (
                          <div className="text-[11px] text-slate-500">
                            Checked <b>{selectedScan.results.sites_checked}</b> platforms
                            {selectedScan.results.routed_via_tor ? " · routed via Tor" : ""}
                          </div>
                        ) : null}

                        <div className="space-y-1 text-xs">
                          <span className="block font-bold text-slate-500 uppercase text-[9px] mb-2">Identified Accounts</span>
                          {selectedScan.results.found_accounts?.map((acc: any, i: number) => (
                            <div key={i} className="flex justify-between items-center bg-emerald-50/50 border border-emerald-100 p-2 rounded">
                              <span className="font-semibold text-emerald-800">{acc.platform}</span>
                              <a href={acc.url} target="_blank" rel="noreferrer" className="text-emerald-700 underline text-[11px] break-all">{acc.url}</a>
                            </div>
                          ))}
                          {selectedScan.results.found_accounts?.length === 0 && (
                            <Empty label="No accounts found on analyzed platforms." />
                          )}
                        </div>
                      </div>
                    )}

                    {selectedScan.scan_type === "domain" && (
                      <div className="space-y-4 text-xs">
                        <div>
                          <span className="block font-bold text-slate-500 uppercase text-[9px] mb-2">Resolved IP Addresses</span>
                          <div className="flex flex-wrap gap-2">
                            {selectedScan.results.ip_addresses?.map((ip: string, i: number) => (
                              <span key={i} className="bg-slate-100 border border-slate-200 px-2 py-1 rounded font-mono font-semibold text-slate-700">{ip}</span>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="block font-bold text-slate-500 uppercase text-[9px] mb-2">DNS Query Records</span>
                          <div className="border border-slate-200 rounded divide-y divide-slate-150">
                            {Object.entries(selectedScan.results.dns_records || {}).map(([key, val]: any, i) => (
                              <div key={i} className="p-2 flex gap-3">
                                <span className="font-bold text-slate-600 w-10 shrink-0 uppercase">{key}</span>
                                <span className="font-mono text-slate-700 text-[11px] break-all">
                                  {Array.isArray(val) ? val.join(" | ") : String(val)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div>
                          <span className="block font-bold text-slate-500 uppercase text-[9px] mb-2">HTTP Web Security Audit</span>
                          <div className="border border-slate-200 rounded divide-y divide-slate-150 bg-slate-50">
                            {Object.entries(selectedScan.results.security_headers || {}).map(([key, val]: any, i) => (
                              <div key={i} className="p-2 flex justify-between gap-3">
                                <span className="font-bold text-slate-600 truncate">{key}</span>
                                <span className={`font-mono text-right text-[10px] break-all font-semibold ${val === "Missing" ? "text-red-600" : "text-emerald-700"}`}>
                                  {String(val)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {selectedScan.scan_type === "metadata" && (
                      <div className="space-y-3 text-xs">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                          <span className="font-bold text-slate-700">Audit Status:</span>
                          {selectedScan.results.has_exif ? (
                            <span className="bg-amber-100 text-amber-900 border border-amber-250 font-bold px-2 py-0.5 rounded text-[10px] flex items-center gap-1">
                              <ShieldAlert className="h-3 w-3 animate-bounce" /> METADATA LEAKS FOUND
                            </span>
                          ) : (
                            <span className="bg-emerald-100 text-emerald-950 font-bold px-2 py-0.5 rounded text-[10px]">CLEAN (NO EXIF)</span>
                          )}
                        </div>

                        {selectedScan.results.file_size_bytes && (
                          <div className="text-[11px] text-slate-600">
                            Analyzed File Size: <span className="font-bold font-mono">{(selectedScan.results.file_size_bytes / 1024).toFixed(1)} KB</span>
                          </div>
                        )}

                        <div className="border border-slate-200 rounded overflow-hidden">
                          <table className="min-w-full divide-y divide-slate-200 text-left">
                            <thead className="bg-slate-50">
                              <tr>
                                <th className="px-3 py-2 text-[9px] uppercase font-bold text-slate-500">EXIF Property</th>
                                <th className="px-3 py-2 text-[9px] uppercase font-bold text-slate-500">Value Extracted</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-mono text-[10px] bg-white">
                              {Object.entries(selectedScan.results.metadata || {}).map(([key, val]: any, i) => {
                                const isGPS = key.toLowerCase().includes("gps");
                                return (
                                  <tr key={i} className={isGPS ? "bg-amber-50/50" : ""}>
                                    <td className="px-3 py-1.5 font-bold text-slate-650 flex items-center gap-1">
                                      {isGPS && <MapPin className="h-3 w-3 text-amber-600 shrink-0" />}
                                      {key}
                                    </td>
                                    <td className={`px-3 py-1.5 break-all ${isGPS ? "text-amber-800 font-bold" : "text-slate-700"}`}>{String(val)}</td>
                                  </tr>
                                );
                              })}
                              {Object.keys(selectedScan.results.metadata || {}).length === 0 && (
                                <tr>
                                  <td colSpan={2} className="px-3 py-4 text-center font-sans font-semibold text-slate-500">
                                    No key-value attributes identified.
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {selectedScan.scan_type === "tor_relay" && (
                      <div className="space-y-4 text-xs">
                        <span className="block font-bold text-slate-700 mb-2">Relay Node Consensus Metrics:</span>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                          {selectedScan.results.relays?.map((relay: any, i: number) => (
                            <div key={i} className="border border-slate-200 rounded p-3 bg-slate-50 space-y-2">
                              <div className="flex items-center justify-between border-b border-slate-200 pb-1.5">
                                <span className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                                  <Globe className="h-4 w-4 text-slate-500" />
                                  {relay.nickname}
                                </span>
                                <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${relay.running ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"}`}>
                                  {relay.running ? "Active" : "Offline"}
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                                <div>
                                  <span className="block text-slate-500 uppercase text-[8px] font-bold">Country</span>
                                  <span className="text-slate-700 font-semibold">{relay.country || "Unknown"}</span>
                                </div>
                                <div>
                                  <span className="block text-slate-500 uppercase text-[8px] font-bold">ASN Network</span>
                                  <span className="text-slate-700 font-semibold">{relay.as_number || "Unknown"}</span>
                                </div>
                                <div className="col-span-2">
                                  <span className="block text-slate-500 uppercase text-[8px] font-bold">OR IP Address</span>
                                  <span className="text-slate-700 font-semibold">{relay.or_addresses?.join(", ")}</span>
                                </div>
                                <div className="col-span-2">
                                  <span className="block text-slate-500 uppercase text-[8px] font-bold">Fingerprint</span>
                                  <span className="text-slate-600 text-[9px] break-all">{relay.fingerprint}</span>
                                </div>
                              </div>
                              
                              <div className="border-t border-slate-200/80 pt-2 space-y-1">
                                <div className="flex justify-between text-[9px] font-bold uppercase text-slate-500">
                                  <span>Consensus Weight</span>
                                  <span className="font-mono text-slate-700">{relay.consensus_weight}</span>
                                </div>
                                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                                  <div
                                    className="bg-emerald-600 h-full"
                                    style={{ width: `${Math.min(100, (relay.consensus_weight / 15000) * 100)}%` }}
                                  ></div>
                                </div>
                              </div>
                            </div>
                          ))}
                          {(!selectedScan.results.relays || selectedScan.results.relays.length === 0) && (
                            <Empty label="No matching Tor relays found." />
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <Empty label="Select a scan from the left panel to examine the digital footprint details" />
            )}
          </section>
        </div>
      )}

      {activeTab === "network" && (
        <div className="flex flex-col gap-5">
          <form
            onSubmit={submitRelayMonitor}
            className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex-1 min-w-[220px]">
              <label className="text-sm font-semibold text-slate-700" htmlFor="anomalySearch">
                Relay search term (nickname / country / AS)
              </label>
              <input
                id="anomalySearch"
                className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600"
                value={anomalySearch}
                onChange={(e) => setAnomalySearch(e.target.value)}
                placeholder="e.g., exit"
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Cpu className="h-4 w-4" />}
              Run PyOD Monitor
            </button>
          </form>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-2">
              <MapPin className="h-5 w-5 text-emerald-600" />
              <h2 className="text-lg font-semibold">Relay Anomaly Geo-Map</h2>
              <span className="ml-auto text-[10px] font-bold uppercase text-slate-400">
                MapLibre GL · TimeSeriesOD
              </span>
            </div>
            <RelayMap anomalies={anomalies} />
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-2">
              <ShieldAlert className="h-5 w-5 text-red-600" />
              <h2 className="text-lg font-semibold">Flagged Relay Anomalies</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Relay</th>
                    <th className="px-3 py-2">Country / AS</th>
                    <th className="px-3 py-2">Anomaly</th>
                    <th className="px-3 py-2">Detector</th>
                    <th className="px-3 py-2 text-right">Δ vs baseline</th>
                    <th className="px-3 py-2 text-right">Score</th>
                    <th className="px-3 py-2 text-center">Severity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {anomalies.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/70">
                      <td className="px-3 py-2.5 font-semibold text-slate-800">
                        {a.nickname || a.fingerprint.slice(0, 10)}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-slate-600">
                        {a.country_name || a.country_code} · {a.as_number}
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
                          {a.anomaly_type.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[10px] text-slate-500">{a.detector}</td>
                      <td className="px-3 py-2.5 text-right font-mono text-slate-700">
                        {a.detail?.pct_change ?? 0}%
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono font-bold text-slate-800">
                        {a.score.toFixed(2)}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                            a.severity === "high"
                              ? "bg-red-100 text-red-800"
                              : a.severity === "medium"
                              ? "bg-amber-100 text-amber-900"
                              : "bg-emerald-100 text-emerald-800"
                          }`}
                        >
                          {a.severity}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {anomalies.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-6 text-center font-semibold text-slate-500">
                        No anomalies yet. Run the PyOD monitor or launch a Tor Relay scan.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {activeTab === "crawler" && (
        <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="flex flex-col gap-5">
            <form onSubmit={submitCrawl} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Globe className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Tor-Routed Crawl</h2>
              </div>
              <label className="text-sm font-semibold text-slate-700" htmlFor="crawlUrl">
                URL (.onion or clearnet)
              </label>
              <input
                id="crawlUrl"
                className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600"
                value={crawlUrl}
                onChange={(e) => setCrawlUrl(e.target.value)}
              />
              <label className="mt-4 block text-sm font-semibold text-slate-700" htmlFor="crawlKw">
                Watch keywords (comma separated)
              </label>
              <input
                id="crawlKw"
                className="mt-2 h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-sm outline-none focus:border-emerald-600"
                value={crawlKeywords}
                onChange={(e) => setCrawlKeywords(e.target.value)}
              />
              <div className="mt-4 flex justify-end border-t border-slate-100 pt-3">
                <button
                  type="submit"
                  disabled={busy}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Launch Crawl
                </button>
              </div>
            </form>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm flex-1">
              <div className="mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Crawl History</h2>
              </div>
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {crawls.length === 0 ? <Empty label="No crawls yet" /> : null}
                {crawls.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSelectedCrawl(c)}
                    className={`w-full rounded-md border p-3 text-left transition-all ${
                      selectedCrawl?.id === c.id
                        ? "border-emerald-600 bg-emerald-50/55"
                        : "border-slate-200 bg-slate-50 hover:bg-slate-100"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-mono text-xs font-semibold text-slate-800">{c.url}</span>
                      <StatusBadge status={c.status} />
                    </div>
                    <div className="mt-1 flex gap-2 text-[10px] font-bold uppercase text-slate-500">
                      {c.is_onion && <span className="text-purple-700">onion</span>}
                      {c.routed_via_tor && <span className="text-emerald-700">via tor</span>}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm min-h-[460px]">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-2">
              <FileSearch className="h-5 w-5 text-emerald-600" />
              <h2 className="text-lg font-semibold">Crawl Result</h2>
            </div>
            {selectedCrawl ? (
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-3 rounded border border-slate-200 bg-slate-50 p-3">
                  <div>
                    <span className="block text-[9px] font-bold uppercase text-slate-500">Title</span>
                    <span className="font-semibold text-slate-800">{selectedCrawl.results?.title || "—"}</span>
                  </div>
                  <div>
                    <span className="block text-[9px] font-bold uppercase text-slate-500">Status</span>
                    <span className="font-mono font-semibold text-slate-800">
                      {selectedCrawl.results?.status_code ?? selectedCrawl.status}
                    </span>
                  </div>
                </div>

                {selectedCrawl.results?.keyword_hits &&
                  Object.keys(selectedCrawl.results.keyword_hits).length > 0 && (
                    <div>
                      <span className="mb-2 block text-[9px] font-bold uppercase text-slate-500">
                        Keyword Hits
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(selectedCrawl.results.keyword_hits).map(([k, v]: any) => (
                          <span
                            key={k}
                            className="rounded bg-amber-100 px-2 py-1 font-mono text-[11px] font-bold text-amber-900"
                          >
                            {k}: {v}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                <div>
                  <span className="mb-1 block text-[9px] font-bold uppercase text-slate-500">
                    Extracted Text
                  </span>
                  <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded border border-slate-200 bg-slate-950 p-3 text-[11px] leading-relaxed text-slate-100">
                    {selectedCrawl.results?.text_snippet || selectedCrawl.error || "No content."}
                  </pre>
                </div>

                {selectedCrawl.results?.links?.length > 0 && (
                  <div>
                    <span className="mb-2 block text-[9px] font-bold uppercase text-slate-500">
                      Discovered Links ({selectedCrawl.results.link_count})
                    </span>
                    <div className="space-y-1">
                      {selectedCrawl.results.links.slice(0, 12).map((l: string, i: number) => (
                        <div key={i} className="truncate font-mono text-[11px] text-emerald-700">
                          {l}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Empty label="Select a crawl to inspect extracted content and links" />
            )}
          </section>
        </div>
      )}

      {activeTab === "censorship" && (
        <div className="flex flex-col gap-5">
          <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm flex flex-col">
              <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-red-650" />
                  <h2 className="text-lg font-semibold">OONI Probe Censorship Incident Logs</h2>
                </div>
                <span className="bg-red-100 text-red-950 font-bold px-2 py-0.5 rounded text-[10px]">CENSORSHIP ALERTING</span>
              </div>
              <div className="flex-1 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Region</th>
                      <th className="px-3 py-2">ASN Network</th>
                      <th className="px-3 py-2">Target Blocked</th>
                      <th className="px-3 py-2">Anomaly Type</th>
                      <th className="px-3 py-2 text-right">Failure Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {incidents.map((inc) => (
                      <tr key={inc.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="px-3 py-2.5 font-bold text-slate-800 flex items-center gap-1.5">
                          <span className="inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-650 font-mono text-[10px] border border-slate-200">{inc.country_code}</span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-slate-600">{inc.asn}</td>
                        <td className="px-3 py-2.5 font-semibold text-slate-800 break-all">{inc.target_domain}</td>
                        <td className="px-3 py-2.5">
                          <span className="bg-amber-100 text-amber-900 border border-amber-200 font-semibold px-2 py-0.5 rounded text-[10px]">{inc.anomaly_type}</span>
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-red-650">{(inc.failure_rate * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                    {incidents.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-550 font-semibold">
                          No OONI censorship incidents recorded. Launch a Domain or Tor Relay scan to seed network anomalies.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm flex flex-col">
              <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-2">
                <Globe className="h-5 w-5 text-emerald-600" />
                <h2 className="text-lg font-semibold">Regional Blocking Ratios</h2>
              </div>
              <div className="flex-1 flex flex-col justify-center space-y-4">
                {incidents.length === 0 ? (
                  <Empty label="No graphs ready yet." />
                ) : (
                  <div className="space-y-3">
                    <span className="text-xs text-slate-650 block">High failure rate anomalies sorted by country and ISP blocking metrics:</span>
                    {incidents.slice(0, 4).map((inc) => (
                      <div key={inc.id} className="space-y-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="font-semibold text-slate-700">{inc.target_domain} ({inc.country_code} - {inc.asn})</span>
                          <span className="font-mono text-red-600 font-bold">{(inc.failure_rate * 100).toFixed(0)}% blocked</span>
                        </div>
                        <div className="w-full bg-slate-100 border border-slate-200 h-3 rounded-full overflow-hidden">
                          <div
                            className="bg-red-600 h-full transition-all duration-500"
                            style={{ width: `${inc.failure_rate * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      )}
    </main>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-sm hover:shadow transition-shadow">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</div>
          <div className="mt-1 text-xl font-bold text-slate-900">{value}</div>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-50 border border-slate-200 text-emerald-600 shrink-0">
          {icon}
        </div>
      </div>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-6 text-center text-sm font-semibold text-slate-500">
      {label}
    </div>
  );
}

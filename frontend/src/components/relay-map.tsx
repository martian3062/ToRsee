"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import type { RelayAnomaly } from "@/lib/types";

const SEVERITY_COLOR: Record<string, string> = {
  high: "#dc2626",
  medium: "#f59e0b",
  low: "#10b981",
};

// Minimal offline-safe style: solid ocean background + graticule-free land box.
// Upgrades to MapLibre demo vector tiles when the network is reachable.
const FALLBACK_STYLE = {
  version: 8 as const,
  sources: {},
  layers: [{ id: "bg", type: "background" as const, paint: { "background-color": "#0f172a" } }],
};

export function RelayMap({ anomalies }: { anomalies: RelayAnomaly[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      if (cancelled || !containerRef.current || mapRef.current) return;

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: "https://demotiles.maplibre.org/style.json",
        center: [8, 47],
        zoom: 1.4,
        attributionControl: false,
      });
      // If the vector style can't load (offline), drop to the flat fallback.
      map.on("error", () => {
        try {
          if (map.isStyleLoaded()) return;
          map.setStyle(FALLBACK_STYLE as any);
        } catch {
          /* noop */
        }
      });
      mapRef.current = map;
    })();
    return () => {
      cancelled = true;
      mapRef.current?.remove?.();
      mapRef.current = null;
    };
  }, []);

  // Re-plot markers whenever anomalies change.
  useEffect(() => {
    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      const map = mapRef.current;
      if (!map) return;
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      anomalies
        .filter((a) => a.latitude != null && a.longitude != null)
        .forEach((a) => {
          const el = document.createElement("div");
          const size = 12 + Math.round(a.score * 16);
          const color = SEVERITY_COLOR[a.severity] ?? "#10b981";
          el.style.cssText = `width:${size}px;height:${size}px;border-radius:9999px;background:${color};opacity:0.85;border:2px solid #f8fafc;box-shadow:0 0 12px ${color};cursor:pointer;`;
          const popup = new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(
            `<div style="font:12px/1.4 system-ui;color:#0f172a">
               <strong>${a.nickname || a.fingerprint.slice(0, 8)}</strong><br/>
               ${a.anomaly_type.replace(/_/g, " ")} · <b style="color:${color}">${a.severity}</b><br/>
               ${a.country_name || a.country_code} ${a.as_number}<br/>
               score ${a.score} · ${a.detail?.pct_change ?? 0}% vs baseline
             </div>`
          );
          const marker = new maplibregl.Marker({ element: el })
            .setLngLat([a.longitude as number, a.latitude as number])
            .setPopup(popup)
            .addTo(map);
          markersRef.current.push(marker);
        });
    })();
  }, [anomalies]);

  return (
    <div className="relative h-[360px] w-full overflow-hidden rounded-lg border border-slate-800">
      <div ref={containerRef} className="h-full w-full" />
      <div className="pointer-events-none absolute right-2 top-2 flex gap-2 rounded bg-slate-900/80 px-2 py-1 text-[10px] font-semibold text-slate-200">
        {(["high", "medium", "low"] as const).map((s) => (
          <span key={s} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: SEVERITY_COLOR[s] }}
            />
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

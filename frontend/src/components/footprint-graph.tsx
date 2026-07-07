"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";

// Reagraph is WebGL/canvas — load client-side only.
const GraphCanvas = dynamic(() => import("reagraph").then((m) => m.GraphCanvas), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
      Loading graph engine…
    </div>
  ),
});

type Detail = { platform: string; found: boolean; url?: string; category?: string };

// Reagraph's theme type is exhaustive; a partial override is cast for brevity.
const GRAPH_THEME: any = {
  canvas: { background: "#020617" },
  node: {
    fill: "#10b981",
    activeFill: "#34d399",
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.4,
    label: { color: "#e2e8f0", activeColor: "#f8fafc", stroke: "#020617" },
  },
  edge: {
    fill: "#334155",
    activeFill: "#10b981",
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.3,
    label: { color: "#94a3b8", activeColor: "#f8fafc", stroke: "#020617" },
  },
  ring: { fill: "#1e293b", activeFill: "#10b981" },
  lasso: { border: "#10b981", background: "rgba(16,185,129,0.1)" },
  arrow: { fill: "#334155", activeFill: "#10b981" },
};

export function FootprintGraph({ username, details }: { username: string; details: Detail[] }) {
  const { nodes, edges } = useMemo(() => {
    const centerId = "root";
    const nodes: { id: string; label: string; fill: string }[] = [
      { id: centerId, label: username, fill: "#059669" },
    ];
    const edges: { id: string; source: string; target: string; fill?: string }[] = [];
    details.forEach((d, i) => {
      const id = `p${i}`;
      nodes.push({ id, label: d.platform, fill: d.found ? "#10b981" : "#334155" });
      edges.push({
        id: `e${i}`,
        source: centerId,
        target: id,
        fill: d.found ? "#10b981" : "#475569",
      });
    });
    return { nodes, edges };
  }, [username, details]);

  return (
    <div className="relative h-64 w-full overflow-hidden rounded border border-slate-800 bg-slate-950">
      <GraphCanvas
        nodes={nodes}
        edges={edges}
        layoutType="radialOut2d"
        labelType="all"
        theme={GRAPH_THEME}
      />
      <div className="pointer-events-none absolute left-2 top-2 flex items-center gap-1 text-[10px] font-bold uppercase text-slate-400">
        <span className="inline-block h-2 w-2 animate-ping rounded-full bg-emerald-500" />
        Reagraph WebGL footprint
      </div>
    </div>
  );
}

import type { Metadata } from "next";

import { MonitoringPanel } from "@/components/monitoring-panel";
import { ProductShell } from "@/components/product-shell";

export const metadata: Metadata = {
  title: "Monitoring",
};

export default function MonitoringPage() {
  return (
    <ProductShell eyebrow="Continuous watch" title="Monitoring">
      <MonitoringPanel />
    </ProductShell>
  );
}

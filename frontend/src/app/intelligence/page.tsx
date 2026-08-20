import type { Metadata } from "next";

import { DrugIntelligencePanel } from "@/components/drug-intelligence-panel";
import { ProductShell } from "@/components/product-shell";

export const metadata: Metadata = {
  title: "Intelligence",
};

export default function IntelligencePage() {
  return (
    <ProductShell eyebrow="Governed casework" title="Drug Intelligence">
      <DrugIntelligencePanel />
    </ProductShell>
  );
}

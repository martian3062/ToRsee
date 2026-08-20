"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { BrandMark } from "@/components/brand-mark";

export function ProductLoader() {
  const pathname = usePathname();
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
    const timeout = window.setTimeout(() => setVisible(false), 560);
    return () => window.clearTimeout(timeout);
  }, [pathname]);

  return (
    <div
      aria-busy={visible}
      aria-label="Loading ToRsy"
      className="route-loader fixed inset-0 z-50 grid place-items-center bg-slate-950"
      data-visible={visible}
    >
      <div className="torsy-loader-mark">
        <BrandMark inverse />
      </div>
    </div>
  );
}

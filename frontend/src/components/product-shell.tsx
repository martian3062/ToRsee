"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BrainCircuit, LayoutDashboard, Radar } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";

const destinations = [
  { href: "/console", label: "Command Center", icon: LayoutDashboard },
  { href: "/intelligence", label: "Intelligence", icon: BrainCircuit },
  { href: "/monitoring", label: "Monitoring", icon: Radar },
];

export function ProductShell({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-16 max-w-[1600px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <Link href="/" aria-label="ToRsy entry" className="shrink-0">
            <BrandMark />
          </Link>
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1" aria-label="Primary navigation">
              {destinations.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-semibold transition-colors ${
                      active
                        ? "bg-slate-950 text-white"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    <span className="hidden sm:inline">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1600px] px-4 py-7 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="text-xs font-bold uppercase text-emerald-700">{eyebrow}</div>
            <h1 className="mt-2 text-2xl font-bold text-slate-950 sm:text-3xl">{title}</h1>
          </div>
          <div className="hidden items-center gap-2 text-xs font-semibold text-slate-500 sm:flex">
            <Activity className="h-4 w-4 text-emerald-600" aria-hidden="true" />
            Operational workspace
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, BrainCircuit, LayoutDashboard, Radar } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";

const workspaces = [
  { href: "/console", label: "Command Center", icon: LayoutDashboard },
  { href: "/intelligence", label: "Intelligence", icon: BrainCircuit },
  { href: "/monitoring", label: "Monitoring", icon: Radar },
];

export function EntryScreen() {
  return (
    <main className="relative isolate flex min-h-screen overflow-hidden bg-slate-950 text-white">
      <Image
        alt="Abstract intelligence network visual"
        className="entry-image -z-20 object-cover opacity-80"
        fill
        priority
        sizes="100vw"
        src="/images/torsy-network-entry.png"
      />
      <div className="absolute inset-0 -z-10 bg-slate-950/60" aria-hidden="true" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-5 py-5 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between gap-4">
          <BrandMark inverse />
          <Link
            href="/console"
            className="inline-flex h-10 items-center gap-2 border border-white/25 bg-black/20 px-3 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white hover:text-slate-950"
          >
            <span className="hidden sm:inline">Open workspace</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </header>

        <section className="flex flex-1 items-center py-10 sm:py-20">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 border border-emerald-300/35 bg-emerald-300/10 px-3 py-1.5 text-xs font-bold uppercase text-emerald-100 sm:mb-5">
              Encrypted-platform intelligence
            </div>
            <h1 className="text-5xl font-bold leading-[0.95] text-white sm:text-6xl">ToRsy</h1>
            <p className="mt-4 max-w-xl text-lg leading-8 text-slate-200 sm:mt-5 sm:text-xl">
              Governed intelligence and continuous monitoring for encrypted-platform investigations.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 sm:mt-9">
              <Link
                href="/console"
                className="inline-flex h-12 items-center gap-3 bg-emerald-300 px-5 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-950/20 hover:bg-emerald-200"
              >
                Enter command center
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/intelligence"
                className="inline-flex h-12 items-center gap-3 border border-white/25 bg-black/20 px-5 text-sm font-bold text-white backdrop-blur-sm hover:bg-white hover:text-slate-950"
              >
                Review intelligence
                <BrainCircuit className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>

        <nav className="grid border-t border-white/20 pt-3 sm:grid-cols-3 sm:pt-4" aria-label="Workspace selection">
          {workspaces.map((workspace) => {
            const Icon = workspace.icon;
            return (
              <Link
                key={workspace.href}
                href={workspace.href}
                className="flex min-h-12 items-center gap-3 border-b border-white/15 py-3 text-sm font-semibold text-white transition-colors hover:text-emerald-200 sm:min-h-14 sm:border-b-0 sm:border-r sm:px-4 sm:py-4 sm:last:border-r-0"
              >
                <Icon className="h-5 w-5 text-emerald-300" aria-hidden="true" />
                {workspace.label}
                <ArrowRight className="ml-auto h-4 w-4" aria-hidden="true" />
              </Link>
            );
          })}
        </nav>
      </div>
    </main>
  );
}

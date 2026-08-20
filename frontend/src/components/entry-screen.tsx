import Image from "next/image";
import Link from "next/link";
import { ArrowRight, BrainCircuit, LayoutDashboard, Radar } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";

const workspaces = [
  { href: "/console", label: "Command Center", icon: LayoutDashboard },
  { href: "/intelligence", label: "Intelligence", icon: BrainCircuit },
  { href: "/monitoring", label: "Monitoring", icon: Radar },
];

export function EntryScreen() {
  return (
    <main className="torsy-entry relative isolate flex min-h-screen overflow-hidden">
      <Image
        alt="Abstract intelligence network visual"
        className="entry-image -z-20 object-cover"
        fill
        priority
        sizes="100vw"
        src="/images/torsy-network-entry.png"
      />
      <div className="entry-overlay absolute inset-0 -z-10" aria-hidden="true" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-5 py-5 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between gap-4">
          <BrandMark inverse />
          <div className="flex items-center gap-2">
            <ThemeToggle variant="entry" />
            <Link href="/console" className="entry-console-link">
              <span className="hidden sm:inline">Open workspace</span>
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </header>

        <section className="flex flex-1 items-center py-10 sm:py-20">
          <div className="max-w-2xl">
            <div className="entry-kicker mb-4 inline-flex items-center gap-2 px-3 py-1.5 text-xs font-bold uppercase sm:mb-5">
              Encrypted-platform intelligence
            </div>
            <h1 className="entry-title text-5xl font-bold leading-[0.95] sm:text-6xl">ToRsy</h1>
            <p className="entry-copy mt-4 max-w-xl text-lg leading-8 sm:mt-5 sm:text-xl">
              Governed intelligence and continuous monitoring for encrypted-platform investigations.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 sm:mt-9">
              <Link
                href="/console"
                className="entry-primary inline-flex h-12 items-center gap-3 px-5 text-sm font-bold"
              >
                Enter command center
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/intelligence"
                className="entry-secondary inline-flex h-12 items-center gap-3 px-5 text-sm font-bold"
              >
                Review intelligence
                <BrainCircuit className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>

        <nav className="entry-nav grid pt-3 sm:grid-cols-3 sm:pt-4" aria-label="Workspace selection">
          {workspaces.map((workspace) => {
            const Icon = workspace.icon;
            return (
              <Link
                key={workspace.href}
                href={workspace.href}
                className="entry-nav-link flex min-h-12 items-center gap-3 py-3 text-sm font-semibold sm:min-h-14 sm:border-b-0 sm:px-4 sm:py-4"
              >
                <Icon className="entry-nav-icon h-5 w-5" aria-hidden="true" />
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

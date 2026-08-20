import { ScanLine } from "lucide-react";

type BrandMarkProps = {
  compact?: boolean;
  inverse?: boolean;
};

export function BrandMark({ compact = false, inverse = false }: BrandMarkProps) {
  const labelTone = inverse ? "text-white" : "text-slate-950";
  const subTone = inverse ? "text-slate-300" : "text-slate-500";

  return (
    <span className="inline-flex items-center gap-2">
      <span className="torsy-brand-icon grid h-9 w-9 place-items-center rounded-md border border-emerald-300/70 bg-emerald-400 text-slate-950 shadow-sm">
        <ScanLine className="h-5 w-5" aria-hidden="true" />
      </span>
      {!compact ? (
        <span className="leading-none">
          <span className={`torsy-brand-name block text-base font-bold ${labelTone}`}>ToRsy</span>
          <span className={`torsy-brand-subtitle mt-1 block text-[10px] font-semibold uppercase ${subTone}`}>The Buddy in the Dark</span>
        </span>
      ) : null}
    </span>
  );
}

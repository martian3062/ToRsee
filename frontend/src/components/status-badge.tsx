import { CheckCircle2, CircleAlert, CircleDashed, FlaskConical } from "lucide-react";

const styles = {
  configured: "border-emerald-200 bg-emerald-50 text-emerald-800",
  missing_key: "border-amber-200 bg-amber-50 text-amber-800",
  disabled: "border-slate-200 bg-slate-100 text-slate-600",
  mocked: "border-cyan-200 bg-cyan-50 text-cyan-800",
  queued: "border-slate-200 bg-slate-100 text-slate-700",
  running: "border-blue-200 bg-blue-50 text-blue-800",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-red-200 bg-red-50 text-red-800",
  fetched: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

const icons = {
  configured: CheckCircle2,
  missing_key: CircleAlert,
  disabled: CircleDashed,
  mocked: FlaskConical,
  queued: CircleDashed,
  running: CircleDashed,
  completed: CheckCircle2,
  failed: CircleAlert,
  fetched: CheckCircle2,
};

type StatusKey = keyof typeof styles;

export function StatusBadge({ status }: { status: StatusKey | string }) {
  const key = (status in styles ? status : "disabled") as StatusKey;
  const Icon = icons[key];
  return (
    <span className={`inline-flex h-7 items-center gap-1 rounded-md border px-2 text-xs font-semibold ${styles[key]}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {status.replace("_", " ")}
    </span>
  );
}

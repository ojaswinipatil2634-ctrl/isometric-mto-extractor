import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  value: number; // 0-1
  className?: string;
}

export function ConfidenceBar({ value, className }: ConfidenceBarProps) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  const color =
    pct >= 80 ? "bg-emerald-600" : pct >= 50 ? "bg-signal-amber" : "bg-red-600";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-graphite-700/10 dark:bg-linework/15">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums text-graphite-700/70 dark:text-linework-dim">
        {pct}%
      </span>
    </div>
  );
}

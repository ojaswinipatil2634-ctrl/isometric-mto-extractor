import { cn } from "@/lib/utils";

interface StatTileProps {
  label: string;
  value: string | number;
  accent?: boolean;
  className?: string;
}

export function StatTile({ label, value, accent, className }: StatTileProps) {
  return (
    <div
      className={cn(
        "rounded-sm border border-graphite-700/15 bg-vellum-50 px-4 py-3 dark:border-linework/15 dark:bg-print-800",
        className
      )}
    >
      <div
        className={cn(
          "font-display text-2xl leading-none",
          accent ? "text-blueprint-600 dark:text-linework" : "text-graphite-900 dark:text-linework"
        )}
      >
        {value}
      </div>
      <div className="mt-1.5 font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
        {label}
      </div>
    </div>
  );
}

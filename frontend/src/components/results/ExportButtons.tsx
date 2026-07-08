import { buildExportUrl } from "@/lib/api";
import { Download } from "lucide-react";

interface ExportButtonsProps {
  runId: number;
}

const FORMATS: { format: "csv" | "json" | "xlsx"; label: string }[] = [
  { format: "csv", label: "CSV" },
  { format: "json", label: "JSON" },
  { format: "xlsx", label: "Excel" },
];

export function ExportButtons({ runId }: ExportButtonsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
        Download
      </span>
      {FORMATS.map(({ format, label }) => (
        <a
          key={format}
          href={buildExportUrl(runId, format)}
          className="flex items-center gap-1.5 rounded-sm border border-graphite-700/20 px-3 py-1.5 text-sm font-medium text-graphite-800 transition-colors hover:bg-graphite-700/5 dark:border-linework/20 dark:text-linework dark:hover:bg-linework/10"
        >
          <Download className="h-3.5 w-3.5" />
          {label}
        </a>
      ))}
    </div>
  );
}

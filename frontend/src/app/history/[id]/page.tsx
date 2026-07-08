"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ApiError, getMtoRun, MTOExtractionResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { StatTile } from "@/components/ui/stat-tile";
import { ExportButtons } from "@/components/results/ExportButtons";
import { Loader2, FileWarning, ArrowLeft } from "lucide-react";

function severityVariant(severity: string): "warning" | "error" {
  return severity === "error" ? "error" : "warning";
}

export default function HistoryDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = Number(params.id);

  const [run, setRun] = useState<MTOExtractionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!Number.isFinite(runId)) return;
    let cancelled = false;
    getMtoRun(runId)
      .then((res) => {
        if (!cancelled) setRun(res);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.code === "RUN_NOT_FOUND") {
          setError(`No extraction run found with id ${runId}.`);
        } else {
          setError("Could not reach the extraction service. Is the backend running?");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-vellum-50 px-6 py-12 dark:bg-print-900">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/history"
          className="mb-6 inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-widest text-graphite-700/60 hover:text-graphite-900 dark:text-linework-dim dark:hover:text-linework"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to history
        </Link>

        {loading ? (
          <div className="flex items-center gap-2 py-16 text-graphite-700/60 dark:text-linework-dim">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="font-mono text-sm">Loading run #{runId}…</span>
          </div>
        ) : error || !run ? (
          <div className="flex flex-col items-center gap-3 rounded-sm border border-signal-amber/40 py-16 text-center">
            <FileWarning className="h-8 w-8 text-signal-amber" />
            <p className="text-sm text-graphite-800 dark:text-linework">{error}</p>
          </div>
        ) : (
          <div className="space-y-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-xs uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                  {run.filename} · {new Date(run.created_at).toLocaleString()}
                </p>
                <h1 className="mt-1 font-display text-2xl text-graphite-900 dark:text-linework">
                  {run.drawing_number ?? `Run #${run.id}`}
                  {run.revision ? ` · Rev. ${run.revision}` : ""}
                </h1>
                {!run.symbol_detection.enabled && (
                  <Badge variant="warning" className="mt-2">
                    Symbol Detection: Not Available (Running OCR + Graph Pipeline)
                  </Badge>
                )}
              </div>
              <ExportButtons runId={run.id} />
            </div>

            <section>
              <h2 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Title block</h2>
              <div className="overflow-hidden rounded-sm border border-graphite-700/15 dark:border-linework/15">
                <table className="w-full text-sm">
                  <tbody>
                    {[
                      ["Line No.", run.line_number],
                      ["Service", run.service],
                      ["Material Class", run.material_class],
                      ["NPS", run.nps_values.join(", ") || null],
                    ].map(([label, value]) => (
                      <tr key={label} className="border-b border-graphite-700/10 last:border-0 dark:border-linework/10">
                        <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-graphite-700/60 dark:text-linework-dim">
                          {label}
                        </td>
                        <td className="px-4 py-2.5 text-graphite-900 dark:text-linework">
                          {value ?? <span className="text-graphite-700/40 dark:text-linework-dim/50">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Pipe network</h2>
              <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
                <StatTile label="Nodes" value={run.node_count} />
                <StatTile label="Runs" value={run.edge_count} />
                <StatTile label="Branches" value={run.branch_count} />
                <StatTile label="Dead ends" value={run.dead_end_count} />
                <StatTile label="Loops" value={run.loop_count} />
                <StatTile label="Connected" value={run.is_fully_connected ? "Yes" : "No"} accent={run.is_fully_connected} />
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Hardware</h2>
              {run.hardware.length === 0 ? (
                <p className="font-mono text-xs text-graphite-700/60 dark:text-linework-dim">
                  No flange hardware generated.
                </p>
              ) : (
                <div className="overflow-hidden rounded-sm border border-graphite-700/15 dark:border-linework/15">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-graphite-700/10 bg-graphite-700/5 dark:border-linework/10 dark:bg-linework/5">
                        <th className="px-4 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                          Item
                        </th>
                        <th className="px-4 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                          Node
                        </th>
                        <th className="px-4 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                          Qty
                        </th>
                        <th className="px-4 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                          Size
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.hardware.map((item, i) => (
                        <tr key={i} className="border-b border-graphite-700/10 last:border-0 dark:border-linework/10">
                          <td className="px-4 py-2 capitalize text-graphite-900 dark:text-linework">
                            {item.item_type.replace("_", " ")}
                          </td>
                          <td className="px-4 py-2 font-mono text-graphite-700/70 dark:text-linework-dim">
                            #{item.node_id}
                          </td>
                          <td className="px-4 py-2 font-mono text-graphite-900 dark:text-linework">{item.quantity}</td>
                          <td className="px-4 py-2 text-graphite-900 dark:text-linework">
                            {item.size}
                            {item.is_estimated && (
                              <Badge variant="warning" className="ml-2">
                                Estimated
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">
                Business rule findings
              </h2>
              {run.violations.length === 0 ? (
                <p className="font-mono text-xs text-emerald-700 dark:text-emerald-400">No issues found.</p>
              ) : (
                <ul className="space-y-2">
                  {run.violations.map((v, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 rounded-sm border border-graphite-700/15 px-3 py-2.5 dark:border-linework/15"
                    >
                      <Badge variant={severityVariant(v.severity)}>{v.rule_code.replace(/_/g, " ")}</Badge>
                      <span className="text-sm text-graphite-800 dark:text-linework">{v.message}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <p className="font-mono text-[10px] uppercase tracking-widest text-graphite-700/50 dark:text-linework-dim/70">
              Original drawing preview isn&apos;t stored - only extraction results are persisted.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}

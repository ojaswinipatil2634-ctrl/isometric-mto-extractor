"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMtoHistory, MTOHistoryItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader2, FileWarning, Inbox } from "lucide-react";

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const [items, setItems] = useState<MTOHistoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getMtoHistory(PAGE_SIZE, offset)
      .then((res) => {
        if (cancelled) return;
        setItems((prev) => (offset === 0 ? res.items : [...prev, ...res.items]));
        setTotalCount(res.total_count);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("Could not reach the extraction service. Is the backend running?");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [offset]);

  const hasMore = items.length < totalCount;

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-vellum-50 px-6 py-12 dark:bg-print-900">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-baseline justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-blueprint-600 dark:text-linework-dim">
              Drawing Register
            </p>
            <h1 className="mt-2 font-display text-3xl text-graphite-900 dark:text-linework">
              Extraction history
            </h1>
          </div>
          {totalCount > 0 && (
            <p className="font-mono text-xs text-graphite-700/60 dark:text-linework-dim">
              {totalCount} run{totalCount === 1 ? "" : "s"}
            </p>
          )}
        </div>

        {loading && items.length === 0 ? (
          <div className="flex items-center gap-2 py-16 text-graphite-700/60 dark:text-linework-dim">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="font-mono text-sm">Loading history…</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center gap-3 rounded-sm border border-signal-amber/40 py-16 text-center">
            <FileWarning className="h-8 w-8 text-signal-amber" />
            <p className="text-sm text-graphite-800 dark:text-linework">{error}</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-sm border border-dashed border-graphite-700/25 py-16 text-center dark:border-linework/25">
            <Inbox className="h-8 w-8 text-graphite-700/40 dark:text-linework/40" />
            <p className="text-sm text-graphite-700/70 dark:text-linework-dim">
              No drawings extracted yet.
            </p>
            <Link href="/" className="text-sm font-medium text-blueprint-600 hover:underline dark:text-linework">
              Upload your first drawing
            </Link>
          </div>
        ) : (
          <>
            <div className="overflow-hidden rounded-sm border border-graphite-700/15 dark:border-linework/15">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-graphite-700/10 bg-graphite-700/5 dark:border-linework/10 dark:bg-linework/5">
                    <th className="px-4 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                      Drawing
                    </th>
                    <th className="px-4 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                      Uploaded
                    </th>
                    <th className="px-4 py-2.5 text-right font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                      Nodes
                    </th>
                    <th className="px-4 py-2.5 text-right font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                      Hardware
                    </th>
                    <th className="px-4 py-2.5 text-right font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
                      Findings
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-graphite-700/10 last:border-0 hover:bg-graphite-700/5 dark:border-linework/10 dark:hover:bg-linework/5"
                    >
                      <td className="px-4 py-3">
                        <Link href={`/history/${item.id}`} className="block">
                          <span className="font-medium text-graphite-900 dark:text-linework">
                            {item.drawing_number ?? item.filename}
                          </span>
                          {item.revision && (
                            <span className="ml-2 font-mono text-xs text-graphite-700/60 dark:text-linework-dim">
                              Rev. {item.revision}
                            </span>
                          )}
                        </Link>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-graphite-700/70 dark:text-linework-dim">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-graphite-900 dark:text-linework">
                        {item.node_count}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-graphite-900 dark:text-linework">
                        {item.hardware_count}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-graphite-900 dark:text-linework">
                        {item.violation_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {hasMore && (
              <div className="mt-6 flex justify-center">
                <Button variant="ghost" onClick={() => setOffset((o) => o + PAGE_SIZE)} disabled={loading}>
                  {loading ? "Loading…" : "Load more"}
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}

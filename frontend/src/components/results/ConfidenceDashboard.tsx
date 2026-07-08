import type { DetectResponse, ExtractedField, MTOExtractionResponse, OcrResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { StatTile } from "@/components/ui/stat-tile";

interface ConfidenceDashboardProps {
  ocr: OcrResponse | null;
  detect: DetectResponse | null;
  mto: MTOExtractionResponse;
}

function severityVariant(severity: string): "warning" | "error" {
  return severity === "error" ? "error" : "warning";
}

export function ConfidenceDashboard({ ocr, detect, mto }: ConfidenceDashboardProps) {
  const fields = ocr?.extracted_fields;
  const fieldRows: [string, ExtractedField | null][] = fields
    ? [
        ["Drawing No.", fields.drawing_number],
        ["Revision", fields.revision],
        ["Line No.", fields.line_number],
        ["Service", fields.service],
        ["Material Class", fields.material_class],
      ]
    : [];

  return (
    <div className="space-y-8">
      {/* OCR title-block fields */}
      <section>
        <h3 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Title block</h3>
        {!ocr ? (
          <p className="font-mono text-xs text-signal-amber">OCR unavailable for this drawing.</p>
        ) : (
          <div className="overflow-hidden rounded-sm border border-graphite-700/15 dark:border-linework/15">
            <table className="w-full text-sm">
              <tbody>
                {fieldRows.map(([label, field]) => (
                  <tr key={label} className="border-b border-graphite-700/10 last:border-0 dark:border-linework/10">
                    <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-graphite-700/60 dark:text-linework-dim">
                      {label}
                    </td>
                    <td className="px-4 py-2.5 text-graphite-900 dark:text-linework">
                      {field?.value ?? <span className="text-graphite-700/40 dark:text-linework-dim/50">—</span>}
                    </td>
                    <td className="px-4 py-2.5">{field && <ConfidenceBar value={field.confidence} />}</td>
                  </tr>
                ))}
                {mto.nps_values.length > 0 && (
                  <tr>
                    <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-graphite-700/60 dark:text-linework-dim">
                      NPS
                    </td>
                    <td className="px-4 py-2.5 text-graphite-900 dark:text-linework" colSpan={2}>
                      {mto.nps_values.join(", ")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Detected symbols */}
      <section>
        <h3 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Detected symbols</h3>
        {!detect || !detect.engine_available ? (
          <p className="font-mono text-xs text-signal-amber">Symbol detection unavailable for this drawing.</p>
        ) : detect.detections.length === 0 ? (
          <p className="font-mono text-xs text-graphite-700/60 dark:text-linework-dim">
            No symbols or fittings were detected.
          </p>
        ) : (
          <div className="space-y-2">
            {Object.entries(detect.counts_by_class).map(([className, count]) => {
              const maxCount = Math.max(...Object.values(detect.counts_by_class));
              return (
                <div key={className} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 font-mono text-xs uppercase tracking-wider text-graphite-700/70 dark:text-linework-dim">
                    {className.replace("_", " ")}
                  </span>
                  <div className="h-3 flex-1 overflow-hidden rounded-sm bg-graphite-700/8 dark:bg-linework/10">
                    <div
                      className="h-full rounded-sm bg-blueprint-500 dark:bg-linework-dim"
                      style={{ width: `${(count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-6 text-right font-mono text-xs tabular-nums text-graphite-900 dark:text-linework">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Graph topology */}
      <section>
        <h3 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Pipe network</h3>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          <StatTile label="Nodes" value={mto.node_count} />
          <StatTile label="Runs" value={mto.edge_count} />
          <StatTile label="Branches" value={mto.branch_count} />
          <StatTile label="Dead ends" value={mto.dead_end_count} />
          <StatTile label="Loops" value={mto.loop_count} />
          <StatTile
            label="Connected"
            value={mto.is_fully_connected ? "Yes" : "No"}
            accent={mto.is_fully_connected}
          />
        </div>
      </section>

      {/* Hardware */}
      <section>
        <h3 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Hardware</h3>
        {mto.hardware.length === 0 ? (
          <p className="font-mono text-xs text-graphite-700/60 dark:text-linework-dim">
            No flange hardware generated (no flanges detected).
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
                {mto.hardware.map((item, i) => (
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

      {/* Violations */}
      <section>
        <h3 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Business rule findings</h3>
        {mto.violations.length === 0 ? (
          <p className="font-mono text-xs text-emerald-700 dark:text-emerald-400">No issues found.</p>
        ) : (
          <ul className="space-y-2">
            {mto.violations.map((v, i) => (
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

      {mto.warnings.length > 0 && (
        <section>
          <h3 className="mb-3 font-display text-lg text-graphite-900 dark:text-linework">Notes</h3>
          <ul className="space-y-1">
            {mto.warnings.map((w, i) => (
              <li key={i} className="font-mono text-xs text-graphite-700/60 dark:text-linework-dim">
                &middot; {w}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

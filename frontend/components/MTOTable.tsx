import { MTOLineItem } from "@/lib/types";
import { csvExportUrl } from "@/lib/api";

interface Props {
  items: MTOLineItem[];
}

export default function MTOTable({ items }: Props) {
  return (
    <div className="rounded-sm border border-blueprint-100 bg-white">
      <div className="flex items-center justify-between border-b border-blueprint-100 p-4">
        <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-blueprint-700">
          Material Take-Off
        </h3>
        <a
          href={csvExportUrl()}
          download="mto_export.csv"
          className="rounded-sm bg-blueprint-600 px-3 py-1.5 font-mono text-xs font-medium text-white transition-colors hover:bg-blueprint-700"
        >
          Export CSV
        </a>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-blueprint-100 bg-blueprint-50/50 font-mono text-[10px] uppercase tracking-wider text-ink/60">
              <th className="px-4 py-2">Component</th>
              <th className="px-4 py-2">NPS</th>
              <th className="px-4 py-2">Rating</th>
              <th className="px-4 py-2 text-right">Quantity</th>
              <th className="px-4 py-2">Unit</th>
              <th className="px-4 py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr
                key={idx}
                className="border-b border-blueprint-100/60 last:border-0 hover:bg-blueprint-50/40"
              >
                <td className="px-4 py-2 font-medium text-ink">{item.component}</td>
                <td className="px-4 py-2 font-mono text-ink/80">{item.nps}</td>
                <td className="px-4 py-2 font-mono text-ink/60">{item.rating || "—"}</td>
                <td className="px-4 py-2 text-right font-mono text-ink">{item.quantity}</td>
                <td className="px-4 py-2 font-mono text-ink/60">{item.unit}</td>
                <td className="px-4 py-2 text-xs text-ink/50">{item.notes || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

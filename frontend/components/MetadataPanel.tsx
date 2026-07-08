import { DrawingMetadata } from "@/lib/types";

interface Props {
  metadata: DrawingMetadata;
  confidence: number;
  mockMode: boolean;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-blueprint-100 py-2 first:border-t-0">
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink/50">
        {label}
      </div>
      <div className="font-mono text-sm font-medium text-ink">{value}</div>
    </div>
  );
}

export default function MetadataPanel({ metadata, confidence, mockMode }: Props) {
  return (
    <div className="rounded-sm border border-blueprint-100 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-blueprint-700">
          Title Block
        </h3>
        <div className="flex items-center gap-2">
          {mockMode && (
            <span className="rounded-sm bg-hazard/20 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide text-hazard">
              Mock Mode
            </span>
          )}
          <span className="rounded-sm bg-blueprint-50 px-2 py-0.5 font-mono text-[10px] font-semibold text-blueprint-700">
            {(confidence * 100).toFixed(0)}% confidence
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
        <Field label="Drawing No." value={metadata.drawing_number} />
        <Field label="Revision" value={metadata.revision} />
        <Field label="Line No." value={metadata.line_number} />
        <Field label="Material Class" value={metadata.material_class} />
        <Field label="Service" value={metadata.service} />
        <Field label="NPS" value={metadata.nps} />
      </div>
    </div>
  );
}

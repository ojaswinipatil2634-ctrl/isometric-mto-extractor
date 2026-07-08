import { MTOSummary } from "@/lib/types";

interface Props {
  summary: MTOSummary;
}

function Card({ label, value, unit }: { label: string; value: number | string; unit?: string }) {
  return (
    <div className="rounded-sm border border-blueprint-100 bg-white p-4">
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink/50">
        {label}
      </div>
      <div className="mt-1 font-mono text-2xl font-semibold text-blueprint-700">
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-ink/50">{unit}</span>}
      </div>
    </div>
  );
}

export default function SummaryCards({ summary }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      <Card label="Total Pipe" value={summary.total_pipe_length_m} unit="m" />
      <Card label="Fittings" value={summary.total_fittings} unit="ea" />
      <Card label="Flanged Joints" value={summary.total_flanged_joints} unit="ea" />
      <Card label="Valves" value={summary.total_valves} unit="ea" />
      <Card label="Gaskets" value={summary.total_gaskets} unit="ea" />
      <Card label="Bolt Sets" value={summary.total_bolt_sets} unit="ea" />
      <Card label="Welds" value={summary.total_welds} unit="ea" />
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-sm border border-blueprint-100 bg-white py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-blueprint-100 border-t-blueprint-600" />
      <p className="font-mono text-sm text-ink/60">Analyzing drawing…</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-sm border border-red-200 bg-red-50 p-6">
      <p className="font-mono text-xs font-semibold uppercase tracking-wide text-red-700">
        Extraction failed
      </p>
      <p className="mt-1 text-sm text-red-800">{message}</p>
      <button
        onClick={onRetry}
        className="mt-3 rounded-sm bg-red-600 px-3 py-1.5 font-mono text-xs font-medium text-white hover:bg-red-700"
      >
        Try again
      </button>
    </div>
  );
}

export function WarningsBanner({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div className="rounded-sm border border-hazard/40 bg-hazard/10 p-3">
      {warnings.map((w, i) => (
        <p key={i} className="font-mono text-xs text-ink/80">
          ⚠ {w}
        </p>
      ))}
    </div>
  );
}

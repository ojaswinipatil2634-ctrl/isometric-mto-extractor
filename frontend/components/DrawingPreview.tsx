"use client";

interface Props {
  file: File;
  previewUrl: string | null;
}

export default function DrawingPreview({ file, previewUrl }: Props) {
  const isPdf = file.name.toLowerCase().endsWith(".pdf");

  return (
    <div className="rounded-sm border border-blueprint-100 bg-white p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-wide text-ink/60">
          Source file
        </span>
        <span className="font-mono text-xs text-ink/60">
          {(file.size / 1024).toFixed(0)} KB
        </span>
      </div>
      <div className="flex h-56 items-center justify-center overflow-hidden rounded-sm bg-slate-100">
        {isPdf ? (
          <div className="flex flex-col items-center gap-1 text-ink/50">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              className="h-10 w-10"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
              />
            </svg>
            <span className="text-xs font-medium">PDF preview unavailable — first page will be analyzed</span>
          </div>
        ) : previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt="Drawing preview"
            className="h-full w-full object-contain"
          />
        ) : (
          <span className="text-xs text-ink/40">Loading preview…</span>
        )}
      </div>
      <p className="mt-2 truncate font-mono text-xs text-ink/70">{file.name}</p>
    </div>
  );
}

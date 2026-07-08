"use client";

import { useEffect, useState } from "react";
import UploadZone from "@/components/UploadZone";
import DrawingPreview from "@/components/DrawingPreview";
import MetadataPanel from "@/components/MetadataPanel";
import SummaryCards from "@/components/SummaryCards";
import MTOTable from "@/components/MTOTable";
import { LoadingState, ErrorState, WarningsBanner } from "@/components/StatusStates";
import { extractDrawing, ApiError } from "@/lib/api";
import { MTOResult } from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<MTOResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
  }, [file]);

  async function handleFile(selected: File) {
    setFile(selected);
    setStatus("loading");
    setErrorMessage("");
    try {
      const data = await extractDrawing(selected);
      setResult(data);
      setStatus("success");
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Unexpected error occurred");
      setStatus("error");
    }
  }

  function handleRetry() {
    if (file) handleFile(file);
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <header className="mb-8 border-b-2 border-blueprint-700 pb-4">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-blueprint-600">
          Isometric Drawing Analysis
        </p>
        <h1 className="mt-1 text-2xl font-bold text-ink sm:text-3xl">
          Material Take-Off Extractor
        </h1>
        <p className="mt-1 text-sm text-ink/60">
          Upload a piping isometric drawing to extract a structured MTO — pipe, fittings,
          flanges, valves, gaskets, bolt sets, and welds.
        </p>
      </header>

      <section className="mb-8">
        <UploadZone onFileSelected={handleFile} disabled={status === "loading"} />
      </section>

      {status === "loading" && <LoadingState />}

      {status === "error" && (
        <ErrorState message={errorMessage} onRetry={handleRetry} />
      )}

      {status === "success" && result && (
        <div className="space-y-6">
          <WarningsBanner warnings={result.warnings} />

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-1">
              {file && <DrawingPreview file={file} previewUrl={previewUrl} />}
            </div>
            <div className="lg:col-span-2">
              <MetadataPanel
                metadata={result.metadata}
                confidence={result.confidence}
                mockMode={result.mock_mode}
              />
            </div>
          </div>

          <SummaryCards summary={result.summary} />

          <MTOTable items={result.line_items} />
        </div>
      )}
    </main>
  );
}

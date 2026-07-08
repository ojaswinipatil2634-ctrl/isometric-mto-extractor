"use client";

import { useCallback, useRef, useState } from "react";
import {
  ApiError,
  DetectResponse,
  MTOExtractionResponse,
  OcrResponse,
  PreprocessResponse,
  detectSymbols,
  preprocessDrawing,
  runFullExtraction,
  runOcr,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DrawingPreview } from "@/components/results/DrawingPreview";
import { ConfidenceDashboard } from "@/components/results/ConfidenceDashboard";
import { ExportButtons } from "@/components/results/ExportButtons";
import { cn } from "@/lib/utils";
import { FileUp, AlertTriangle, Loader2 } from "lucide-react";

const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg"];

type Status = "idle" | "dragging" | "uploading" | "done" | "error";

interface Results {
  preprocess: PreprocessResponse;
  ocr: OcrResponse | null;
  detect: DetectResponse | null;
  mto: MTOExtractionResponse;
}

export function UploadForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<Results | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const runUpload = useCallback(async (file: File) => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setStatus("error");
      setErrorMessage(`"${file.name}" is not a supported drawing format. Use PDF, PNG, or JPG.`);
      return;
    }

    setSelectedFile(file);
    setStatus("uploading");
    setErrorMessage(null);

    try {
      // The full pipeline persists the run (Phase 8) and is the source of
      // truth for extracted fields/graph/hardware/violations. Preprocess,
      // OCR, and detect are run alongside it purely to give this page a
      // drawing preview, bounding-box overlay, and per-field confidence -
      // each is independently best-effort, so one being unavailable
      // (e.g. no trained YOLO weights) never blocks the others.
      const [preprocess, ocrSettled, detectSettled, mto] = await Promise.all([
        preprocessDrawing(file),
        runOcr(file).then(
          (v) => ({ ok: true as const, value: v }),
          () => ({ ok: false as const, value: null })
        ),
        detectSymbols(file).then(
          (v) => ({ ok: true as const, value: v }),
          () => ({ ok: false as const, value: null })
        ),
        runFullExtraction(file),
      ]);

      setResults({
        preprocess,
        ocr: ocrSettled.ok ? ocrSettled.value : null,
        detect: detectSettled.ok ? detectSettled.value : null,
        mto,
      });
      setStatus("done");
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Could not reach the extraction service. Is the backend running?");
      }
      setStatus("error");
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) void runUpload(file);
    },
    [runUpload]
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void runUpload(file);
    },
    [runUpload]
  );

  const reset = () => {
    setStatus("idle");
    setResults(null);
    setErrorMessage(null);
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  if (status === "done" && results) {
    return (
      <div className="w-full max-w-4xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
              {selectedFile?.name}
            </p>
            <p className="font-display text-xl text-graphite-900 dark:text-linework">
              {results.mto.drawing_number ?? "Extraction complete"}
              {results.mto.revision ? ` · Rev. ${results.mto.revision}` : ""}
            </p>
            {!results.mto.symbol_detection.enabled && (
              <Badge variant="warning" className="mt-2">
                Symbol Detection: Not Available (Running OCR + Graph Pipeline)
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-3">
            <ExportButtons runId={results.mto.id} />
            <Button variant="ghost" size="sm" onClick={reset}>
              Upload another
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <DrawingPreview
            imageBase64={results.preprocess.preview_image_base64}
            width={results.preprocess.processed_width}
            height={results.preprocess.processed_height}
            detections={results.detect?.detections ?? []}
            detectionsAvailable={Boolean(results.detect?.engine_available)}
          />
          <ConfidenceDashboard ocr={results.ocr} detect={results.detect} mto={results.mto} />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl">
      {/* Ruler strip - signature element referencing the drafting table */}
      <div className="mb-2 flex h-5 items-end border-b border-graphite-700/20 dark:border-linework/20">
        {Array.from({ length: 21 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 border-l border-graphite-700/15 dark:border-linework/15"
            style={{ height: i % 5 === 0 ? "100%" : "50%" }}
          />
        ))}
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (status === "idle") setStatus("dragging");
        }}
        onDragLeave={() => status === "dragging" && setStatus("idle")}
        onDrop={onDrop}
        className={cn(
          "drafting-grid relative flex min-h-[280px] flex-col items-center justify-center rounded-sm border-2 border-dashed p-10 text-center transition-colors",
          status === "dragging" && "border-blueprint-500 bg-blueprint-500/5",
          status === "idle" && "border-graphite-700/30 dark:border-linework/30",
          status === "uploading" && "border-blueprint-500/50",
          status === "error" && "border-signal-amber/60"
        )}
      >
        <span className="pointer-events-none absolute left-2 top-2 h-3 w-3 border-l-2 border-t-2 border-graphite-700/40 dark:border-linework/40" />
        <span className="pointer-events-none absolute right-2 top-2 h-3 w-3 border-r-2 border-t-2 border-graphite-700/40 dark:border-linework/40" />
        <span className="pointer-events-none absolute bottom-2 left-2 h-3 w-3 border-b-2 border-l-2 border-graphite-700/40 dark:border-linework/40" />
        <span className="pointer-events-none absolute bottom-2 right-2 h-3 w-3 border-b-2 border-r-2 border-graphite-700/40 dark:border-linework/40" />

        {status === "idle" || status === "dragging" ? (
          <>
            <FileUp className="mb-4 h-10 w-10 text-graphite-700/60 dark:text-linework/60" />
            <p className="font-display text-lg text-graphite-900 dark:text-linework">
              Drop the isometric drawing here
            </p>
            <p className="mt-1 font-mono text-xs uppercase tracking-widest text-graphite-700/50 dark:text-linework-dim">
              PDF · PNG · JPG — up to 25MB
            </p>
            <Button className="mt-6" onClick={() => inputRef.current?.click()}>
              Choose file
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={onFileChange}
              className="hidden"
            />
          </>
        ) : status === "uploading" ? (
          <>
            <Loader2 className="mb-4 h-10 w-10 animate-spin text-blueprint-500 dark:text-linework" />
            <p className="font-display text-lg text-graphite-900 dark:text-linework">
              Extracting {selectedFile?.name}…
            </p>
            <p className="mt-1 font-mono text-xs uppercase tracking-widest text-graphite-700/50 dark:text-linework-dim">
              OCR · symbol detection · pipe graph · business rules
            </p>
          </>
        ) : (
          <>
            <AlertTriangle className="mb-4 h-10 w-10 text-signal-amber" />
            <p className="font-display text-lg text-graphite-900 dark:text-linework">Extraction failed</p>
            <p className="mt-2 max-w-sm text-sm text-graphite-700/70 dark:text-linework-dim">{errorMessage}</p>
            <Button variant="ghost" className="mt-4" onClick={reset}>
              Try again
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

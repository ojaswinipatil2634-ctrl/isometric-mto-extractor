"use client";

import { useCallback, useRef, useState } from "react";

const ACCEPTED = [".png", ".jpg", ".jpeg", ".pdf"];
const MAX_MB = 20;

interface Props {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export default function UploadZone({ onFileSelected, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndEmit = useCallback(
    (file: File) => {
      const lower = file.name.toLowerCase();
      const okExt = ACCEPTED.some((ext) => lower.endsWith(ext));
      if (!okExt) {
        setLocalError(`Unsupported file type. Use ${ACCEPTED.join(", ")}`);
        return;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setLocalError(`File exceeds ${MAX_MB}MB limit`);
        return;
      }
      setLocalError(null);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (disabled) return;
          const file = e.dataTransfer.files?.[0];
          if (file) validateAndEmit(file);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`
          relative flex flex-col items-center justify-center gap-2 rounded-sm
          border-2 border-dashed px-6 py-14 text-center transition-colors
          bg-iso-grid bg-iso-grid
          ${dragOver ? "border-blueprint-600 bg-blueprint-50" : "border-blueprint-100"}
          ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-blueprint-400"}
        `}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          className="h-10 w-10 text-blueprint-600"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3.75 3.75 0 0 1 4.377 3.658c0 .246-.02.487-.057.72A4.5 4.5 0 0 1 18 19.5H6.75Z"
          />
        </svg>
        <p className="font-medium text-ink">
          Drop your isometric drawing here, or click to browse
        </p>
        <p className="text-sm text-ink/60">PNG, JPG, or PDF · up to {MAX_MB}MB</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          className="hidden"
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) validateAndEmit(file);
            e.target.value = "";
          }}
        />
      </div>
      {localError && (
        <p className="mt-2 text-sm font-medium text-red-600">{localError}</p>
      )}
    </div>
  );
}

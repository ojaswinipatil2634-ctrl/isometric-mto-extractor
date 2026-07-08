"use client";

import { useMemo, useState } from "react";
import type { Detection } from "@/lib/api";

interface DrawingPreviewProps {
  imageBase64: string;
  width: number;
  height: number;
  detections: Detection[];
  detectionsAvailable: boolean;
}

// Distinct colors per fitting class so an overlay with several classes
// stays readable - keyed by name rather than index so a class always
// gets the same color across different drawings.
const CLASS_COLORS: Record<string, string> = {
  elbow: "#5B8FB9",
  tee: "#C77A32",
  reducer: "#8E6FB0",
  gate_valve: "#3F9B6E",
  globe_valve: "#3F9B6E",
  check_valve: "#3F9B6E",
  flange: "#D14D4D",
  support: "#6B7280",
  weld: "#B08900",
};

function colorFor(className: string): string {
  return CLASS_COLORS[className] ?? "#5B8FB9";
}

export function DrawingPreview({
  imageBase64,
  width,
  height,
  detections,
  detectionsAvailable,
}: DrawingPreviewProps) {
  const [showOverlay, setShowOverlay] = useState(true);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const imageSrc = useMemo(() => `data:image/png;base64,${imageBase64}`, [imageBase64]);

  return (
    <div className="relative">
      <div className="mb-2 flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-widest text-graphite-700/60 dark:text-linework-dim">
          Processed drawing - {width}&times;{height}px
        </p>
        {detectionsAvailable && detections.length > 0 && (
          <button
            onClick={() => setShowOverlay((v) => !v)}
            className="font-mono text-[10px] uppercase tracking-widest text-blueprint-600 hover:underline dark:text-linework-dim"
          >
            {showOverlay ? "Hide" : "Show"} overlay
          </button>
        )}
      </div>

      <div className="relative overflow-hidden rounded-sm border border-graphite-700/20 dark:border-linework/20">
        <svg viewBox={`0 0 ${width} ${height}`} className="block w-full" role="img" aria-label="Processed drawing">
          <image href={imageSrc} width={width} height={height} />
          {showOverlay &&
            detections.map((d, i) => {
              const color = colorFor(d.class_name);
              const isHovered = hoveredIndex === i;
              return (
                <g key={i}>
                  <rect
                    x={d.bbox.x1}
                    y={d.bbox.y1}
                    width={d.bbox.x2 - d.bbox.x1}
                    height={d.bbox.y2 - d.bbox.y1}
                    fill="none"
                    stroke={color}
                    strokeWidth={isHovered ? 3 : 2}
                    onMouseEnter={() => setHoveredIndex(i)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className="cursor-pointer"
                  />
                  {isHovered && (
                    <text
                      x={d.bbox.x1}
                      y={Math.max(12, d.bbox.y1 - 4)}
                      fontSize={Math.max(12, height / 45)}
                      fontFamily="var(--font-mono)"
                      fill={color}
                      className="select-none"
                    >
                      {d.class_name} · {Math.round(d.confidence * 100)}%
                    </text>
                  )}
                </g>
              );
            })}
        </svg>
      </div>

      {!detectionsAvailable && (
        <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-signal-amber">
          Symbol detection unavailable - no trained weights configured
        </p>
      )}
    </div>
  );
}

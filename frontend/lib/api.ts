import { MTOResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API || "http://localhost:8000";

export class ApiError extends Error {}

export async function extractDrawing(file: File): Promise<MTOResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/extract`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || `Extraction failed (${res.status})`);
  }
  return res.json();
}

export async function fetchHealth(): Promise<{ status: string; mock_mode: boolean; model: string }> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new ApiError("Health check failed");
  return res.json();
}

export function csvExportUrl(): string {
  return `${API_BASE}/api/export/csv`;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.code = body.error.code;
    this.status = status;
  }
}

async function postFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body: formData });
  const body = await response.json();

  if (!response.ok) {
    throw new ApiError(response.status, body as ApiErrorBody);
  }
  return body as T;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  const body = await response.json();

  if (!response.ok) {
    throw new ApiError(response.status, body as ApiErrorBody);
  }
  return body as T;
}

// ---------------------------------------------------------------------------
// Health (Phase 1)
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error(`Health check failed with status ${response.status}`);
  return response.json();
}

// ---------------------------------------------------------------------------
// Preprocess (Phase 2) - the exact image detections/OCR run against
// ---------------------------------------------------------------------------

export interface PreprocessResponse {
  status: string;
  filename: string;
  original_width: number;
  original_height: number;
  processed_width: number;
  processed_height: number;
  skew_angle_corrected_degrees: number;
  resize_scale_factor: number;
  steps_applied: string[];
  processing_time_ms: number;
  processed_image_base64: string;
  preview_image_base64: string;
}

export async function preprocessDrawing(file: File): Promise<PreprocessResponse> {
  return postFile<PreprocessResponse>("/preprocess", file);
}

// ---------------------------------------------------------------------------
// OCR (Phase 3)
// ---------------------------------------------------------------------------

export interface OcrLine {
  text: string;
  confidence: number;
  bounding_box: number[][];
}

export interface ExtractedField {
  value: string;
  confidence: number;
  source_text: string;
  bounding_box: number[][];
}

export interface OcrResponse {
  status: string;
  filename: string;
  raw_text_lines: OcrLine[];
  extracted_fields: {
    drawing_number: ExtractedField | null;
    revision: ExtractedField | null;
    line_number: ExtractedField | null;
    service: ExtractedField | null;
    material_class: ExtractedField | null;
    nps: ExtractedField | null;
    dimensions: ExtractedField[];
  };
  processing_time_ms: number;
}

export async function runOcr(file: File): Promise<OcrResponse> {
  return postFile<OcrResponse>("/ocr", file);
}

// ---------------------------------------------------------------------------
// Detection (Phase 4)
// ---------------------------------------------------------------------------

export interface Detection {
  class_name: string;
  confidence: number;
  bbox: { x1: number; y1: number; x2: number; y2: number };
}

export interface DetectResponse {
  status: string;
  filename: string;
  engine_available: boolean;
  detections: Detection[];
  detection_count: number;
  counts_by_class: Record<string, number>;
  confidence_threshold: number;
  warnings: string[];
  processing_time_ms: number;
}

export async function detectSymbols(file: File): Promise<DetectResponse> {
  return postFile<DetectResponse>("/detect", file);
}

// ---------------------------------------------------------------------------
// Business rules (Phase 7) - shapes reused by the /mto response below
// ---------------------------------------------------------------------------

export interface HardwareLineItem {
  item_type: string;
  node_id: number;
  quantity: number;
  size: string;
  is_estimated: boolean;
}

export interface RuleViolation {
  rule_code: string;
  severity: string;
  message: string;
  node_ids: number[];
}

// ---------------------------------------------------------------------------
// Full MTO extraction + persistence (Phase 8)
// ---------------------------------------------------------------------------

export interface MTOExtractionResponse {
  id: number;
  status: string;
  filename: string;
  created_at: string;

  drawing_number: string | null;
  revision: string | null;
  line_number: string | null;
  service: string | null;
  material_class: string | null;
  nps_values: string[];

  node_count: number;
  edge_count: number;
  branch_count: number;
  dead_end_count: number;
  loop_count: number;
  is_fully_connected: boolean;

  hardware: HardwareLineItem[];
  violations: RuleViolation[];
  duplicate_fitting_count: number;

  // Informational only - the rest of this response (metadata, graph,
  // hardware, violations, CSV/JSON/XLSX export) is always produced
  // whether or not symbol detection ran; `enabled: false` just means no
  // trained YOLO weights were available for this run.
  symbol_detection: {
    enabled: boolean;
    reason: string | null;
  };

  warnings: string[];
  processing_time_ms: number;
}

export async function runFullExtraction(file: File): Promise<MTOExtractionResponse> {
  return postFile<MTOExtractionResponse>("/mto", file);
}

export interface MTOHistoryItem {
  id: number;
  filename: string;
  created_at: string;
  drawing_number: string | null;
  revision: string | null;
  node_count: number;
  hardware_count: number;
  violation_count: number;
}

export interface MTOHistoryResponse {
  items: MTOHistoryItem[];
  total_count: number;
  limit: number;
  offset: number;
}

export async function getMtoHistory(limit = 20, offset = 0): Promise<MTOHistoryResponse> {
  return getJson<MTOHistoryResponse>(`/mto/history?limit=${limit}&offset=${offset}`);
}

export async function getMtoRun(id: number): Promise<MTOExtractionResponse> {
  return getJson<MTOExtractionResponse>(`/mto/${id}`);
}

export type ExportFormat = "csv" | "json" | "xlsx";

export function buildExportUrl(id: number, format: ExportFormat): string {
  return `${API_BASE_URL}/mto/${id}/export?format=${format}`;
}

// ---------------------------------------------------------------------------
// Gemini verification (Phase 9)
// ---------------------------------------------------------------------------

export interface VerificationResponse {
  status: string;
  filename: string;
  available: boolean;
  corrections: string[];
  missing_items: string[];
  ocr_flags: string[];
  warnings: string[];
  processing_time_ms: number;
}

export async function verifyExtraction(file: File): Promise<VerificationResponse> {
  return postFile<VerificationResponse>("/verify", file);
}

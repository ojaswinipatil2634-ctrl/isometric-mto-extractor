export interface DrawingMetadata {
  drawing_number: string;
  revision: string;
  line_number: string;
  material_class: string;
  service: string;
  nps: string;
}

export interface MTOLineItem {
  component: string;
  nps: string;
  unit: string;
  quantity: number;
  rating?: string | null;
  notes?: string | null;
}

export interface MTOSummary {
  total_pipe_length_m: number;
  total_fittings: number;
  total_flanged_joints: number;
  total_gaskets: number;
  total_bolt_sets: number;
  total_valves: number;
  total_welds: number;
}

export interface MTOResult {
  metadata: DrawingMetadata;
  line_items: MTOLineItem[];
  summary: MTOSummary;
  confidence: number;
  mock_mode: boolean;
  warnings: string[];
}

export type DrawingFormat = "IFC" | "DWG" | "DXF" | "RVT";
export type DrawingStatus = "UPLOADED" | "PROCESSING" | "PARSED" | "FAILED";
export type BOQItemStatus = "DRAFT" | "APPROVED";

export interface Drawing {
  id: string;
  project_id: string;
  original_filename: string;
  format: DrawingFormat;
  status: DrawingStatus;
  file_size_bytes: number;
  error_message: string | null;
  parsed_at: string | null;
  created_at: string;
}

export interface DrawingElement {
  id: string;
  ifc_global_id: string | null;
  ifc_type: string;
  name: string | null;
  raw_material_text: string | null;
  unit: string | null;
  quantity: number | string; 
  properties: Record<string, unknown>;
}

export interface BOQVersion {
  id: string;
  project_id: string;
  drawing_id: string | null;
  label: string;
  created_at: string;
}

export interface BOQItem {
  id: string;
  boq_version_id: string;
  drawing_element_id: string | null;
  material_name: string;
  category: string | null;
  unit: string;
  quantity: number | string;
  unit_rate: number | string | null;
  status: BOQItemStatus;
  version: number;
  approved_at: string | null;
}

export interface BOQItemUpdateRequest {
  version: number;
  material_name?: string;
  category?: string | null;
  unit?: string;
  quantity?: number;
  unit_rate?: number | null;
}

export interface MaterialLibraryEntry {
  id: string;
  raw_text: string;
  normalized_name: string;
  category: string | null;
  default_unit: string | null;
}

export interface MaterialLibraryCreateRequest {
  raw_text: string;
  normalized_name: string;
  category?: string | null;
  default_unit?: string | null;
}
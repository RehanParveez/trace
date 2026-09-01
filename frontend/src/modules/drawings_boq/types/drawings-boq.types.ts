export type DrawingFormat = "IFC" | "DWG" | "DXF" | "RVT";
export type DrawingStatus = "UPLOADED" | "PROCESSING" | "PARSED" | "FAILED";
export type BOQItemStatus = "DRAFT" | "APPROVED";
export type BOQItemType = "MATERIAL" | "LABOUR" | "CUSTOM";
export type BOQVersionStatus = "ACTIVE" | "SUPERSEDED";

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
  status: BOQVersionStatus;
  covered_area_sqft: number | string | null;
  export_meta: BOQExportMeta;
  created_at: string;
}

export interface BOQExportMeta {
  company_name?: string;
  client_name?: string;
  project_title?: string;
  location?: string;
  plot_size?: string;
  storeys?: string;
  prepared_by?: string;
  checked_by?: string;
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
  item_type: BOQItemType;
  created_by_user_id: string | null;
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

export interface BOQCustomItemCreateRequest {
  material_name: string;
  category?: string | null;
  unit: string;
  quantity: number;
  unit_rate?: number | null;
}

export interface BOQVersionUpdateRequest {
  covered_area_sqft?: number | null;
  export_meta?: Partial<BOQExportMeta>;
}

export interface BOQSummary {
  boq_version_id: string;
  materials_total: number | string;
  labour_total: number | string;
  custom_total: number | string;
  grand_total: number | string;
  cost_per_sqft: number | string | null;
  covered_area_sqft: number | string | null;
  amount_in_words: string;
  unpriced_item_count: number;
  unapproved_item_count: number;
  item_count: number;
}

export interface MaterialLibraryEntry {
  id: string;
  raw_text: string;
  normalized_name: string;
  category: string | null;
  default_unit: string | null;
  default_rate: number | string | null;
}

export interface MaterialLibraryCreateRequest {
  raw_text: string;
  normalized_name: string;
  category?: string | null;
  default_unit?: string | null;
  default_rate?: number | null;
}

export interface MaterialLibraryUpdateRequest {
  normalized_name?: string;
  category?: string | null;
  default_unit?: string | null;
  default_rate?: number | null;
}

export interface LabourRate {
  id: string;
  trade: string;
  unit: string;
  rate: number | string;
}

export interface LabourRateCreateRequest {
  trade: string;
  unit: string;
  rate: number;
}

export interface LabourRateUpdateRequest {
  trade?: string;
  unit?: string;
  rate?: number;
}
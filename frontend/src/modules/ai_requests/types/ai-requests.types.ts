export type AIRequestPurpose = "MATERIAL_NORMALIZATION" | "CAPTION_PARSING" | "PHOTO_TAGGING";
export type AIEntityType = "DRAWING_ELEMENT" | "SITE_PHOTO" | "WHATSAPP_MESSAGE";
export type AIProvider = "OLLAMA" | "ANTHROPIC";
export type AIResponseStatus = "SUCCEEDED" | "FAILED";

export interface AIResponseSummary {
  status: AIResponseStatus;
  parsed_output: Record<string, unknown> | null;
  error_message: string | null;
  latency_ms: number | null;
}

export interface AIRequestEntry {
  id: string;
  purpose: AIRequestPurpose;
  entity_type: AIEntityType | null;
  entity_id: string | null;
  provider: AIProvider;
  model: string;
  requested_by: string | null;
  created_at: string;
  response: AIResponseSummary | null;
}

export interface AIUsageSummary {
  total_requests: number;
  succeeded: number;
  failed: number;
  average_latency_ms: number | null;
}

export interface AIRequestListParams {
  purpose?: AIRequestPurpose;
  entityType?: AIEntityType;
  entityId?: string;
  skip?: number;
  limit?: number;
}
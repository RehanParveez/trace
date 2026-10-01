import { authenticatedRequest } from "./client";
import type {AIEntityType, AIRequestPurpose, AIRequestRecord, AIUsageSummary,
} from "./types";

export type AIRequestListParams = {
  purpose?: AIRequestPurpose;
  entity_type?: AIEntityType;
  entity_id?: string;
  skip?: number;
  limit?: number;
};

function buildQuery(params: AIRequestListParams): string {
  const query = new URLSearchParams();

  if (params.purpose) query.set("purpose", params.purpose);
  if (params.entity_type) query.set("entity_type", params.entity_type);
  if (params.entity_id) query.set("entity_id", params.entity_id);
  if (params.skip !== undefined) query.set("skip", String(params.skip));
  if (params.limit !== undefined) query.set("limit", String(params.limit));

  const value = query.toString();
  return value ? `?${value}` : "";
}

export function listAIRequests(
  params: AIRequestListParams = {},
): Promise<AIRequestRecord[]> {
  return authenticatedRequest<AIRequestRecord[]>(
    `/ai-requests${buildQuery(params)}`,
  );
}

export function getAIUsageSummary(): Promise<AIUsageSummary> {
  return authenticatedRequest<AIUsageSummary>(
    "/ai-requests/usage-summary",
  );
}
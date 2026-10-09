import { authenticatedRequest } from "./client";
import type {AnalysisCreatePayload, AnalysisUpdatePayload, BulkRateInput, RateAnalysis, RateImportResult,
} from "./types";

const BASE = "/drawings-boq";

export function createAnalysis(bookId: string, payload: AnalysisCreatePayload): Promise<RateAnalysis> {
  return authenticatedRequest<RateAnalysis>(`${BASE}/rate-books/${bookId}/analyses`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAnalysis(analysisId: string, payload: AnalysisUpdatePayload): Promise<RateAnalysis> {
  return authenticatedRequest<RateAnalysis>(`${BASE}/rate-analyses/${analysisId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function bulkUpsertRates(bookId: string, items: BulkRateInput[]): Promise<RateImportResult> {
  return authenticatedRequest<RateImportResult>(`${BASE}/rate-books/${bookId}/items/bulk`, {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}
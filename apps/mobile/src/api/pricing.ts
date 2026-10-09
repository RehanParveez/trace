import { authenticatedRequest } from "./client";
import type { DrawingUpload } from "./drawingsBoq";
import type {AnalysisBreakdown, PriceVersionOptions, PriceVersionResult, PricingSummary, RateAnalysis, RateBook, RateBookPayload, RateBookStatus, RateEscalation, RateEscalationPayload,
  RateExplain, RateImportResult, RateItem, RateItemPayload, RateOverride, RateOverridePayload,
} from "./types";

const BASE = "/drawings-boq";

function send(method: string, payload?: unknown): RequestInit {
  return payload === undefined ? { method } : { method, body: JSON.stringify(payload) };
}

export function compact<T extends object>(value: T): T {
  const out: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    if (item === undefined || item === null) continue;
    if (typeof item === "string" && item.trim() === "") continue;
    out[key] = typeof item === "string" ? item.trim() : item;
  }
  return out as T;
}

export function listRateBooks(status?: RateBookStatus): Promise<RateBook[]> {
  const suffix = status ? `?status=${status}` : "";
  return authenticatedRequest<RateBook[]>(`${BASE}/rate-books${suffix}`);
}

export function getRateBook(bookId: string): Promise<RateBook> {
  return authenticatedRequest<RateBook>(`${BASE}/rate-books/${bookId}`);
}

export function createRateBook(payload: RateBookPayload): Promise<RateBook> {
  return authenticatedRequest<RateBook>(`${BASE}/rate-books`, send("POST", compact(payload)));
}

export function updateRateBook(bookId: string, payload: RateBookPayload): Promise<RateBook> {
  return authenticatedRequest<RateBook>(
    `${BASE}/rate-books/${bookId}`,
    send("PATCH", compact(payload)),
  );
}

export function deleteRateBook(bookId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/rate-books/${bookId}`, send("DELETE"));
}

export function publishRateBook(bookId: string): Promise<RateBook> {
  return authenticatedRequest<RateBook>(`${BASE}/rate-books/${bookId}/publish`, send("POST"));
}

export function newRateBookVersion(bookId: string): Promise<RateBook> {
  return authenticatedRequest<RateBook>(`${BASE}/rate-books/${bookId}/new-version`, send("POST"));
}

export function archiveRateBook(bookId: string): Promise<RateBook> {
  return authenticatedRequest<RateBook>(`${BASE}/rate-books/${bookId}/archive`, send("POST"));
}

export function listRateItems(bookId: string, search?: string): Promise<RateItem[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (search?.trim()) query.set("q", search.trim());
  return authenticatedRequest<RateItem[]>(`${BASE}/rate-books/${bookId}/items?${query.toString()}`);
}

export function addRateItem(bookId: string, payload: RateItemPayload): Promise<RateItem> {
  return authenticatedRequest<RateItem>(
    `${BASE}/rate-books/${bookId}/items`,
    send("POST", compact(payload)),
  );
}

export function updateRateItem(itemId: string, payload: RateItemPayload): Promise<RateItem> {
  return authenticatedRequest<RateItem>(`${BASE}/rate-items/${itemId}`, send("PATCH", compact(payload)));
}

export function deleteRateItem(itemId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/rate-items/${itemId}`, send("DELETE"));
}

export function importRateItemsCsv(bookId: string, file: DrawingUpload): Promise<RateImportResult> {
  const form = new FormData();
  form.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.mimeType ?? "text/csv",
  } as unknown as Blob);
  return authenticatedRequest<RateImportResult>(`${BASE}/rate-books/${bookId}/import`, {
    method: "POST",
    body: form,
  });
}

export function listEscalations(bookId: string): Promise<RateEscalation[]> {
  return authenticatedRequest<RateEscalation[]>(`${BASE}/rate-books/${bookId}/escalations`);
}

export function addEscalation(
  bookId: string,
  payload: RateEscalationPayload,
): Promise<RateEscalation> {
  return authenticatedRequest<RateEscalation>(
    `${BASE}/rate-books/${bookId}/escalations`,
    send("POST", compact(payload)),
  );
}

export function deleteEscalation(escalationId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/rate-escalations/${escalationId}`, send("DELETE"));
}

export function listAnalyses(bookId: string): Promise<RateAnalysis[]> {
  return authenticatedRequest<RateAnalysis[]>(`${BASE}/rate-books/${bookId}/analyses`);
}

export function getAnalysis(analysisId: string): Promise<RateAnalysis> {
  return authenticatedRequest<RateAnalysis>(`${BASE}/rate-analyses/${analysisId}`);
}

export function getAnalysisBreakdown(analysisId: string): Promise<AnalysisBreakdown> {
  return authenticatedRequest<AnalysisBreakdown>(`${BASE}/rate-analyses/${analysisId}/breakdown`);
}

export function computeAnalysis(analysisId: string): Promise<RateAnalysis> {
  return authenticatedRequest<RateAnalysis>(`${BASE}/rate-analyses/${analysisId}/compute`, send("POST"));
}

export function applyAnalysis(analysisId: string): Promise<RateItem> {
  return authenticatedRequest<RateItem>(`${BASE}/rate-analyses/${analysisId}/apply`, send("POST"));
}

export function deleteAnalysis(analysisId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/rate-analyses/${analysisId}`, send("DELETE"));
}

export function listRateOverrides(
  projectId: string,
  includeRevoked: boolean,
): Promise<RateOverride[]> {
  const suffix = includeRevoked ? "?include_revoked=true" : "";
  return authenticatedRequest<RateOverride[]>(`${BASE}/projects/${projectId}/rate-overrides${suffix}`);
}

export function createRateOverride(
  projectId: string,
  payload: RateOverridePayload,
): Promise<RateOverride> {
  return authenticatedRequest<RateOverride>(
    `${BASE}/projects/${projectId}/rate-overrides`,
    send("POST", compact(payload)),
  );
}

export function revokeRateOverride(overrideId: string, reason: string): Promise<RateOverride> {
  return authenticatedRequest<RateOverride>(
    `${BASE}/rate-overrides/${overrideId}/revoke`,
    send("POST", { reason: reason.trim() }),
  );
}

export function priceVersionWith(
  versionId: string,
  options: PriceVersionOptions,
): Promise<PriceVersionResult> {
  const body: Record<string, unknown> = { overwrite_manual: options.overwriteManual === true };
  if (options.rateBookIds && options.rateBookIds.length > 0) body.rate_book_ids = options.rateBookIds;
  if (options.asOf?.trim()) body.as_of = options.asOf.trim();
  return authenticatedRequest<PriceVersionResult>(
    `${BASE}/boq-versions/${versionId}/price`,
    send("POST", body),
  );
}

export function getPricingSummary(versionId: string): Promise<PricingSummary> {
  return authenticatedRequest<PricingSummary>(`${BASE}/boq-versions/${versionId}/pricing`);
}

export function getRateResolution(itemId: string, asOf?: string): Promise<RateExplain> {
  const suffix = asOf?.trim() ? `?as_of=${encodeURIComponent(asOf.trim())}` : "";
  return authenticatedRequest<RateExplain>(`${BASE}/boq-items/${itemId}/rate-resolution${suffix}`);
}
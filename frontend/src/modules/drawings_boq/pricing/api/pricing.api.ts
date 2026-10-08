import { apiClient } from "../../../../shared/api/client";
import type { Page } from "../../types/drawings-boq.types";
import type {AnalysisBreakdown, AnalysisCreatePayload, AnalysisUpdatePayload, DiffOptions, DiffResult, EscalationCreatePayload, OverrideCreatePayload, PriceVersionPayload, PriceVersionResult,
  PricingSummary, ProjectRateOverride, RateAnalysis, RateBook, RateBookCreatePayload, RateBookFilters, RateBookUpdatePayload, RateEscalation, RateExplain, RateImportResult, RateItem,
   RateItemFilters, RateItemInput, RateItemUpdatePayload,
} from "../types/pricing.types";

const BASE = "/drawings-boq";

async function getPage<T>(url: string, params: Record<string, unknown>): Promise<Page<T>> {
  const response = await apiClient.get<T[]>(url, { params });
  const cursor = response.headers["x-next-cursor"];
  return {
    items: response.data,
    nextCursor: typeof cursor === "string" && cursor.length > 0 ? cursor : null,
  };
}

export const pricingApi = {
  async listRateBooks(params: RateBookFilters & { limit?: number; after?: string | null } = {}): Promise<Page<RateBook>> {
    return getPage<RateBook>(`${BASE}/rate-books`, {
      status: params.status ?? undefined,
      owner: params.owner ?? "all",
      limit: params.limit,
      after: params.after ?? undefined,
    });
  },
  async getRateBook(id: string): Promise<RateBook> {
    return (await apiClient.get<RateBook>(`${BASE}/rate-books/${id}`)).data;
  },
  async createRateBook(payload: RateBookCreatePayload): Promise<RateBook> {
    return (await apiClient.post<RateBook>(`${BASE}/rate-books`, payload)).data;
  },
  async updateRateBook(id: string, payload: RateBookUpdatePayload): Promise<RateBook> {
    return (await apiClient.patch<RateBook>(`${BASE}/rate-books/${id}`, payload)).data;
  },
  async deleteRateBook(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/rate-books/${id}`);
  },
  async publishRateBook(id: string): Promise<RateBook> {
    return (await apiClient.post<RateBook>(`${BASE}/rate-books/${id}/publish`, {})).data;
  },
  async newRateBookVersion(id: string): Promise<RateBook> {
    return (await apiClient.post<RateBook>(`${BASE}/rate-books/${id}/new-version`, {})).data;
  },
  async archiveRateBook(id: string): Promise<RateBook> {
    return (await apiClient.post<RateBook>(`${BASE}/rate-books/${id}/archive`, {})).data;
  },

  async listRateItems(
    bookId: string,
    params: RateItemFilters & { limit?: number; after?: string | null } = {},
  ): Promise<Page<RateItem>> {
    return getPage<RateItem>(`${BASE}/rate-books/${bookId}/items`, {
      q: params.q || undefined,
      trade: params.trade || undefined,
      include_inactive: params.include_inactive ? true : undefined,
      limit: params.limit,
      after: params.after ?? undefined,
    });
  },
  async addRateItem(bookId: string, payload: RateItemInput): Promise<RateItem> {
    return (await apiClient.post<RateItem>(`${BASE}/rate-books/${bookId}/items`, payload)).data;
  },
  async bulkUpsertRateItems(bookId: string, items: RateItemInput[]): Promise<RateImportResult> {
    return (await apiClient.post<RateImportResult>(`${BASE}/rate-books/${bookId}/items/bulk`, { items })).data;
  },
  async importRateItemsCsv(bookId: string, file: File): Promise<RateImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    return (
      await apiClient.post<RateImportResult>(`${BASE}/rate-books/${bookId}/import`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
    ).data;
  },
  async updateRateItem(itemId: string, payload: RateItemUpdatePayload): Promise<RateItem> {
    return (await apiClient.patch<RateItem>(`${BASE}/rate-items/${itemId}`, payload)).data;
  },
  async deleteRateItem(itemId: string): Promise<void> {
    await apiClient.delete(`${BASE}/rate-items/${itemId}`);
  },

  async listEscalations(bookId: string): Promise<RateEscalation[]> {
    return (await apiClient.get<RateEscalation[]>(`${BASE}/rate-books/${bookId}/escalations`)).data;
  },
  async addEscalation(bookId: string, payload: EscalationCreatePayload): Promise<RateEscalation> {
    return (await apiClient.post<RateEscalation>(`${BASE}/rate-books/${bookId}/escalations`, payload)).data;
  },
  async deleteEscalation(escalationId: string): Promise<void> {
    await apiClient.delete(`${BASE}/rate-escalations/${escalationId}`);
  },

  async listAnalyses(bookId: string): Promise<RateAnalysis[]> {
    return (await apiClient.get<RateAnalysis[]>(`${BASE}/rate-books/${bookId}/analyses`)).data;
  },
  async createAnalysis(bookId: string, payload: AnalysisCreatePayload): Promise<RateAnalysis> {
    return (await apiClient.post<RateAnalysis>(`${BASE}/rate-books/${bookId}/analyses`, payload)).data;
  },
  async updateAnalysis(analysisId: string, payload: AnalysisUpdatePayload): Promise<RateAnalysis> {
    return (await apiClient.patch<RateAnalysis>(`${BASE}/rate-analyses/${analysisId}`, payload)).data;
  },
  async deleteAnalysis(analysisId: string): Promise<void> {
    await apiClient.delete(`${BASE}/rate-analyses/${analysisId}`);
  },
  async getAnalysisBreakdown(analysisId: string): Promise<AnalysisBreakdown> {
    return (await apiClient.get<AnalysisBreakdown>(`${BASE}/rate-analyses/${analysisId}/breakdown`)).data;
  },
  async computeAnalysis(analysisId: string): Promise<RateAnalysis> {
    return (await apiClient.post<RateAnalysis>(`${BASE}/rate-analyses/${analysisId}/compute`, {})).data;
  },
  async applyAnalysis(analysisId: string): Promise<RateItem> {
    return (await apiClient.post<RateItem>(`${BASE}/rate-analyses/${analysisId}/apply`, {})).data;
  },

  async listOverrides(
    projectId: string,
    params: { include_revoked?: boolean; limit?: number; after?: string | null } = {},
  ): Promise<Page<ProjectRateOverride>> {
    return getPage<ProjectRateOverride>(`${BASE}/projects/${projectId}/rate-overrides`, {
      include_revoked: params.include_revoked ? true : undefined,
      limit: params.limit,
      after: params.after ?? undefined,
    });
  },
  async createOverride(projectId: string, payload: OverrideCreatePayload): Promise<ProjectRateOverride> {
    return (await apiClient.post<ProjectRateOverride>(`${BASE}/projects/${projectId}/rate-overrides`, payload)).data;
  },
  async revokeOverride(overrideId: string, reason: string): Promise<ProjectRateOverride> {
    return (await apiClient.post<ProjectRateOverride>(`${BASE}/rate-overrides/${overrideId}/revoke`, { reason })).data;
  },

  async priceVersion(versionId: string, payload: PriceVersionPayload = {}): Promise<PriceVersionResult> {
    return (await apiClient.post<PriceVersionResult>(`${BASE}/boq-versions/${versionId}/price`, payload)).data;
  },
  async getPricingSummary(versionId: string): Promise<PricingSummary> {
    return (await apiClient.get<PricingSummary>(`${BASE}/boq-versions/${versionId}/pricing`)).data;
  },
  async explainItemRate(itemId: string, asOf?: string | null): Promise<RateExplain> {
    return (
      await apiClient.get<RateExplain>(`${BASE}/boq-items/${itemId}/rate-resolution`, {
        params: { as_of: asOf || undefined },
      })
    ).data;
  },

  async diffVersions(versionA: string, versionB: string, options: DiffOptions = {}): Promise<DiffResult> {
    return (
      await apiClient.get<DiffResult>(`${BASE}/boq-versions/${versionA}/diff/${versionB}`, {
        params: {
          include_unchanged: options.include_unchanged ? true : undefined,
          include_elements: options.include_elements === false ? false : undefined,
        },
      })
    ).data;
  },
};

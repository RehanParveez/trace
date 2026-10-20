import { apiClient } from "../../../../../shared/api/client";
import type { Page } from "../../../types/drawings-boq.types";
import type {BulkPayload, ChapterSummary, CompareMatch, CompareResult, HistoryResult, ImportRow, ImportStatus, PublishPayload, PublishResult, RateGapsResult, RateImport, Readiness,
  RefreshPayload, RefreshResult, ReparsePayload, RowFilter, RowUpdatePayload, SuggestResult, UploadPayload,
} from "../types/schedules.types";

const BASE = "/drawings-boq";

async function getPage<T>(url: string, params: Record<string, unknown>): Promise<Page<T>> {
  const response = await apiClient.get<T[]>(url, { params });
  const cursor = response.headers["x-next-cursor"];
  return {
    items: response.data,
    nextCursor: typeof cursor === "string" && cursor.length > 0 ? cursor : null,
  };
}

export interface RowQuery {
  filter: RowFilter;
  chapter: string | null;
  q: string;
}

export const schedulesApi = {
  async upload(payload: UploadPayload): Promise<RateImport> {
    const form = new FormData();
    form.append("file", payload.file);
    form.append("layout_profile", payload.layout_profile);
    form.append("first_page", String(payload.first_page));
    if (payload.last_page) form.append("last_page", String(payload.last_page));
    for (const key of ["book_code", "book_name", "edition", "jurisdiction", "province", "city", "currency", "effective_from", "effective_to"] as const) {
      const value = payload[key].trim();
      if (value) form.append(key, value);
    }
    return (await apiClient.post<RateImport>(`${BASE}/rate-imports`, form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
  async list(params: { status?: ImportStatus | null; limit?: number; after?: string | null } = {}): Promise<Page<RateImport>> {
    return getPage<RateImport>(`${BASE}/rate-imports`, { status: params.status ?? undefined, limit: params.limit, after: params.after ?? undefined });
  },
  async get(id: string): Promise<RateImport> {
    return (await apiClient.get<RateImport>(`${BASE}/rate-imports/${id}`)).data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/rate-imports/${id}`);
  },
  async reparse(id: string, payload: ReparsePayload): Promise<RateImport> {
    return (await apiClient.post<RateImport>(`${BASE}/rate-imports/${id}/reparse`, payload)).data;
  },
  async rows(id: string, query: RowQuery, after: string | null, limit = 100): Promise<Page<ImportRow>> {
    return getPage<ImportRow>(`${BASE}/rate-imports/${id}/rows`, {
      filter: query.filter === "all" ? undefined : query.filter,
      chapter: query.chapter ?? undefined,
      q: query.q.trim() || undefined,
      after: after ?? undefined,
      limit,
    });
  },
  async chapters(id: string): Promise<ChapterSummary[]> {
    return (await apiClient.get<ChapterSummary[]>(`${BASE}/rate-imports/${id}/chapters`)).data;
  },
  async updateRow(id: string, rowId: string, payload: RowUpdatePayload): Promise<ImportRow> {
    return (await apiClient.patch<ImportRow>(`${BASE}/rate-imports/${id}/rows/${rowId}`, payload)).data;
  },
  async bulk(id: string, payload: BulkPayload): Promise<{ changed: number; skipped: number }> {
    return (await apiClient.post<{ changed: number; skipped: number }>(`${BASE}/rate-imports/${id}/rows/bulk`, payload)).data;
  },
  async suggest(id: string): Promise<SuggestResult> {
    return (await apiClient.post<SuggestResult>(`${BASE}/rate-imports/${id}/suggest`, {})).data;
  },
  async readiness(id: string, includeUnmapped: boolean): Promise<Readiness> {
    return (await apiClient.get<Readiness>(`${BASE}/rate-imports/${id}/readiness`, { params: { include_unmapped: includeUnmapped } })).data;
  },
  async publish(id: string, payload: PublishPayload): Promise<PublishResult> {
    return (await apiClient.post<PublishResult>(`${BASE}/rate-imports/${id}/publish`, payload)).data;
  },

  async exportBook(bookId: string, format: "csv" | "xlsx"): Promise<Blob> {
    return (await apiClient.get<Blob>(`${BASE}/rate-books/${bookId}/export`, { params: { format }, responseType: "blob" })).data;
  },
  async compare(bookId: string, otherId: string, matchOn: CompareMatch): Promise<CompareResult> {
    return (await apiClient.get<CompareResult>(`${BASE}/rate-books/${bookId}/compare/${otherId}`, { params: { match_on: matchOn } })).data;
  },
  async history(bookId: string, code: string, unit: string): Promise<HistoryResult> {
    return (await apiClient.get<HistoryResult>(`${BASE}/rate-books/${bookId}/history`, { params: { work_item_code: code, unit: unit || undefined } })).data;
  },
  async refresh(bookId: string, payload: RefreshPayload): Promise<RefreshResult> {
    return (await apiClient.post<RefreshResult>(`${BASE}/rate-books/${bookId}/refresh`, payload)).data;
  },
  async rateGaps(versionId: string): Promise<RateGapsResult> {
    return (await apiClient.get<RateGapsResult>(`${BASE}/boq-versions/${versionId}/rate-gaps`)).data;
  },
};

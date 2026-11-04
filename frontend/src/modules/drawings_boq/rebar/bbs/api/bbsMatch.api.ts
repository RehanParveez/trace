import { apiClient } from "../../../../../shared/api/client";
import type { BbsDecisions, ConfirmPayload, MatchFilters, MatchItemList, MatchRun } from "../types/bbsMatch.types";

const B = "/drawings-boq";
export const MATCH_PAGE_SIZE = 100;

export const bbsMatchApi = {
  async run(documentId: string) {
    return (await apiClient.post<MatchRun>(`${B}/bbs/${documentId}/match`)).data;
  },

  async latest(documentId: string) {
    return (await apiClient.get<MatchRun | null>(`${B}/bbs/${documentId}/match`)).data;
  },

  async items(documentId: string, filters: MatchFilters) {
    return (await apiClient.get<MatchItemList>(`${B}/bbs/${documentId}/match/items`, {
      params: { kind: filters.kind || undefined, family: filters.family || undefined, page: filters.page, page_size: MATCH_PAGE_SIZE },
    })).data;
  },

  async confirm(documentId: string, payload: ConfirmPayload) {
    return (await apiClient.post<MatchRun>(`${B}/bbs/${documentId}/match/confirm`, payload)).data;
  },

  async forget(documentId: string, group: string) {
    return (await apiClient.delete<MatchRun>(`${B}/bbs/${documentId}/match/confirm`, { params: { group } })).data;
  },

  async decisions(projectId: string) {
    return (await apiClient.get<BbsDecisions>(`${B}/projects/${projectId}/bbs-decisions`)).data;
  },

  async putFloorMap(projectId: string, value: Record<string, string[]>) {
    return (await apiClient.put<BbsDecisions>(`${B}/projects/${projectId}/bbs-decisions/bbs_floor_map`, { value })).data;
  },
};

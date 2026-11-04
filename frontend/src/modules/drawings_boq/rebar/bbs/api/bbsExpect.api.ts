import { apiClient } from "../../../../../shared/api/client";
import type { BbsDecisions } from "../types/bbsMatch.types";
import type { ExpectFilters, ExpectRun, ExpectationList } from "../types/bbsExpect.types";

const B = "/drawings-boq";
export const EXPECT_PAGE_SIZE = 100;

export const bbsExpectApi = {
  async run(documentId: string) {
    return (await apiClient.post<ExpectRun>(`${B}/bbs/${documentId}/expect`)).data;
  },

  async latest(documentId: string) {
    return (await apiClient.get<ExpectRun | null>(`${B}/bbs/${documentId}/expect`)).data;
  },

  async items(documentId: string, filters: ExpectFilters) {
    return (await apiClient.get<ExpectationList>(`${B}/bbs/${documentId}/expect/items`, {
      params: {
        member_class: filters.member_class || undefined, complete: filters.complete === "" ? undefined : filters.complete === "yes",
        page: filters.page, page_size: EXPECT_PAGE_SIZE,
      },
    })).data;
  },

  async putDecision(projectId: string, key: string, value: unknown) {
    return (await apiClient.put<BbsDecisions>(`${B}/projects/${projectId}/bbs-decisions/${key}`, { value })).data;
  },

  async clearDecision(projectId: string, key: string) {
    return (await apiClient.delete<BbsDecisions>(`${B}/projects/${projectId}/bbs-decisions/${key}`)).data;
  },
};

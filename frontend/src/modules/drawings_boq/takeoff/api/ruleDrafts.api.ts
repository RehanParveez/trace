import { apiClient } from "../../../../shared/api/client";
import type { DraftFile, RuleDrafts } from "../types/ruleDrafts.types";

const BASE = "/drawings-boq/rule-book/drafts";

export const ruleDraftsApi = {
  async list(): Promise<RuleDrafts> {
    return (await apiClient.get<RuleDrafts>(BASE)).data;
  },
  async import(body: DraftFile): Promise<RuleDrafts> {
    return (await apiClient.post<RuleDrafts>(BASE, body)).data;
  },
  async confirm(id: string, value?: unknown): Promise<RuleDrafts> {
    return (await apiClient.post<RuleDrafts>(`${BASE}/${id}/confirm`, value === undefined ? {} : { value })).data;
  },
  async reject(id: string): Promise<RuleDrafts> {
    return (await apiClient.delete<RuleDrafts>(`${BASE}/${id}`)).data;
  },
};

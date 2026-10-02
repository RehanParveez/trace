import { apiClient } from "../../../../shared/api/client";
import type {Convention, Formula, PublishResult, RecipeUpsertPayload, ResolvedProfile, RuleSet, RuleSetCreatePayload, RuleSetDetail, RuleSetDraftUpdatePayload, ValidationResult, WorkItem,
 WorkItemCreatePayload, WorkItemUpdatePayload,
} from "../types/standards.types";

const BASE = "/drawings-boq";

export const standardsApi = {
  async listRuleSets(): Promise<RuleSet[]> {
    return (await apiClient.get<RuleSet[]>(`${BASE}/rule-sets`)).data;
  },
  async getRuleSet(id: string): Promise<RuleSetDetail> {
    return (await apiClient.get<RuleSetDetail>(`${BASE}/rule-sets/${id}`)).data;
  },
  async createDraft(payload: RuleSetCreatePayload): Promise<RuleSetDetail> {
    return (await apiClient.post<RuleSetDetail>(`${BASE}/rule-sets`, payload)).data;
  },
  async updateDraft(id: string, payload: RuleSetDraftUpdatePayload): Promise<RuleSetDetail> {
    return (await apiClient.put<RuleSetDetail>(`${BASE}/rule-sets/${id}`, payload)).data;
  },
  async clone(id: string): Promise<RuleSetDetail> {
    return (await apiClient.post<RuleSetDetail>(`${BASE}/rule-sets/${id}/clone`, {})).data;
  },
  async validate(id: string): Promise<ValidationResult> {
    return (await apiClient.post<ValidationResult>(`${BASE}/rule-sets/${id}/validate`, {})).data;
  },
  async publish(id: string): Promise<PublishResult> {
    return (await apiClient.post<PublishResult>(`${BASE}/rule-sets/${id}/publish`, {})).data;
  },
  async upsertRecipe(id: string, payload: RecipeUpsertPayload): Promise<RuleSetDetail> {
    return (await apiClient.post<RuleSetDetail>(`${BASE}/rule-sets/${id}/recipes`, payload)).data;
  },
  async deleteRecipe(id: string, recipeId: string): Promise<void> {
    await apiClient.delete(`${BASE}/rule-sets/${id}/recipes/${recipeId}`);
  },
  async getResolved(params: { code?: string; as_of?: string }): Promise<ResolvedProfile> {
    return (await apiClient.get<ResolvedProfile>(`${BASE}/standards/resolved`, { params })).data;
  },
  async listFormulas(): Promise<Formula[]> {
    return (await apiClient.get<Formula[]>(`${BASE}/formulas`)).data;
  },
  async listConventions(): Promise<Convention[]> {
    return (await apiClient.get<Convention[]>(`${BASE}/conventions`)).data;
  },
  async listWorkItems(): Promise<WorkItem[]> {
    return (await apiClient.get<WorkItem[]>(`${BASE}/work-items`)).data;
  },
  async createWorkItem(payload: WorkItemCreatePayload): Promise<WorkItem> {
    return (await apiClient.post<WorkItem>(`${BASE}/work-items`, payload)).data;
  },
  async updateWorkItem(id: string, payload: WorkItemUpdatePayload): Promise<WorkItem> {
    return (await apiClient.patch<WorkItem>(`${BASE}/work-items/${id}`, payload)).data;
  },
};
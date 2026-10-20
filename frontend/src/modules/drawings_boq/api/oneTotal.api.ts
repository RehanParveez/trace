import { apiClient } from "../../../shared/api/client";

export type OneTotalPrefer = "DRAWING" | "MODEL" | "BOTH";
export type OneTotalRuleKind = "COLUMN" | "FOOTING" | "BEAM" | "SLAB" | "STAIR" | "ITEM";

export interface OneTotalRule {
  id: string;
  kind: OneTotalRuleKind;
  mark: string;
  level_name: string;
  prefer: OneTotalPrefer;
  note?: string | null;
  updated_at?: string | null;
}

export interface OneTotalRuleBody {
  kind: OneTotalRuleKind;
  mark?: string;
  level_name?: string;
  prefer: OneTotalPrefer;
  note?: string | null;
}

export interface OneTotalSources {
  model_drawings: number;
  pdf_drawings: number;
  both: boolean;
  one_total: { value: 0 | 1; source: "user" | "detected" | "default" };
  needs_attention: boolean;
  rules: number;
}

const base = (projectId: string) => `/drawings-boq/projects/${projectId}/one-total`;

export const oneTotalApi = {
  async rules(projectId: string): Promise<OneTotalRule[]> {
    if (!projectId) throw new Error("Project ID is required");
    return (await apiClient.get<{ rules: OneTotalRule[] }>(`${base(projectId)}/rules`)).data.rules;
  },
  async setRule(projectId: string, body: OneTotalRuleBody): Promise<OneTotalRule[]> {
    if (!projectId) throw new Error("Project ID is required");
    return (await apiClient.put<{ rules: OneTotalRule[] }>(`${base(projectId)}/rules`, body)).data.rules;
  },
  async removeRule(projectId: string, ruleId: string): Promise<OneTotalRule[]> {
    if (!projectId) throw new Error("Project ID is required");
    return (await apiClient.delete<{ rules: OneTotalRule[] }>(`${base(projectId)}/rules/${ruleId}`)).data.rules;
  },
  async sources(projectId: string): Promise<OneTotalSources> {
    if (!projectId) throw new Error("Project ID is required");
    return (await apiClient.get<OneTotalSources>(`${base(projectId)}/sources`)).data;
  },
};

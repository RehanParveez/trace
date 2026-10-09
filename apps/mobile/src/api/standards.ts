import { authenticatedRequest } from "./client";
import type {Convention, FinishOptions, Formula, RecipePayload, RulePublishResult, RuleSet, RuleSetDetail, RuleValidation, WorkItemFull,
} from "./types";

const BASE = "/drawings-boq";

function send(method: string, payload?: unknown): RequestInit {
  return payload === undefined ? { method } : { method, body: JSON.stringify(payload) };
}

export function listRuleSets(): Promise<RuleSet[]> {
  return authenticatedRequest<RuleSet[]>(`${BASE}/rule-sets`);
}

export function getRuleSet(ruleSetId: string): Promise<RuleSetDetail> {
  return authenticatedRequest<RuleSetDetail>(`${BASE}/rule-sets/${ruleSetId}`);
}

export function createRuleSetDraft(payload: Record<string, unknown>): Promise<RuleSetDetail> {
  return authenticatedRequest<RuleSetDetail>(`${BASE}/rule-sets`, send("POST", payload));
}

export function updateRuleSetDraft(
  ruleSetId: string,
  payload: Record<string, unknown>,
): Promise<RuleSetDetail> {
  return authenticatedRequest<RuleSetDetail>(`${BASE}/rule-sets/${ruleSetId}`, send("PUT", payload));
}

export function cloneRuleSet(ruleSetId: string): Promise<RuleSetDetail> {
  return authenticatedRequest<RuleSetDetail>(`${BASE}/rule-sets/${ruleSetId}/clone`, send("POST"));
}

export function validateRuleSet(ruleSetId: string): Promise<RuleValidation> {
  return authenticatedRequest<RuleValidation>(`${BASE}/rule-sets/${ruleSetId}/validate`, send("POST"));
}

export function publishRuleSet(ruleSetId: string): Promise<RulePublishResult> {
  return authenticatedRequest<RulePublishResult>(`${BASE}/rule-sets/${ruleSetId}/publish`, send("POST"));
}

export function upsertRecipe(ruleSetId: string, payload: RecipePayload): Promise<RuleSetDetail> {
  return authenticatedRequest<RuleSetDetail>(`${BASE}/rule-sets/${ruleSetId}/recipes`, send("POST", payload));
}

export function deleteRecipe(ruleSetId: string, recipeId: string): Promise<void> {
  return authenticatedRequest<void>(`${BASE}/rule-sets/${ruleSetId}/recipes/${recipeId}`, send("DELETE"));
}

export function getResolvedStandards(code?: string, asOf?: string): Promise<Record<string, unknown>> {
  const query = new URLSearchParams();
  if (code?.trim()) query.set("code", code.trim());
  if (asOf?.trim()) query.set("as_of", asOf.trim());
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return authenticatedRequest<Record<string, unknown>>(`${BASE}/standards/resolved${suffix}`);
}

export function listFormulas(): Promise<Formula[]> {
  return authenticatedRequest<Formula[]>(`${BASE}/formulas`);
}

export function listConventions(): Promise<Convention[]> {
  return authenticatedRequest<Convention[]>(`${BASE}/conventions`);
}

export function getFinishOptions(): Promise<FinishOptions> {
  return authenticatedRequest<FinishOptions>(`${BASE}/finish-options`);
}

export function listWorkItemsFull(): Promise<WorkItemFull[]> {
  return authenticatedRequest<WorkItemFull[]>(`${BASE}/work-items`);
}

export function createWorkItem(payload: Record<string, unknown>): Promise<WorkItemFull> {
  return authenticatedRequest<WorkItemFull>(`${BASE}/work-items`, send("POST", payload));
}

export function updateWorkItem(workItemId: string, payload: Record<string, unknown>): Promise<WorkItemFull> {
  return authenticatedRequest<WorkItemFull>(`${BASE}/work-items/${workItemId}`, send("PATCH", payload));
}
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { standardsApi } from "../api/standards.api";
import type {RecipeUpsertPayload, RuleSetCreatePayload, RuleSetDraftUpdatePayload, WorkItemCreatePayload, WorkItemUpdatePayload, ResolvedProfile, 
} from "../types/standards.types";
import type { Recipe, RecipeItemType, WorkItem, Formula } from "../types/standards.types";

export const standardsKeys = {
  all: ["standards"] as const,
  ruleSets: () => [...standardsKeys.all, "rule-sets"] as const,
  ruleSet: (id: string) => [...standardsKeys.all, "rule-set", id] as const,
  workItems: () => [...standardsKeys.all, "work-items"] as const,
  formulas: () => [...standardsKeys.all, "formulas"] as const,
  conventions: () => [...standardsKeys.all, "conventions"] as const,
  resolved: (code: string, asOf: string) => [...standardsKeys.all, "resolved", code, asOf] as const,
};

export function useRuleSets() {
  return useQuery({ queryKey: standardsKeys.ruleSets(), queryFn: standardsApi.listRuleSets });
}

export function useRuleSet(id: string) {
  return useQuery({ queryKey: standardsKeys.ruleSet(id), queryFn: () => standardsApi.getRuleSet(id), enabled: Boolean(id) });
}

export function useWorkItems() {
  return useQuery({ queryKey: standardsKeys.workItems(), queryFn: standardsApi.listWorkItems });
}

export function useFormulas() {return useQuery<Formula[]>({
 queryKey: standardsKeys.formulas(), queryFn: standardsApi.listFormulas,
    staleTime: 5 * 60_000,
 });
}

export function useConventions() {
  return useQuery({ queryKey: standardsKeys.conventions(), queryFn: standardsApi.listConventions, staleTime: 5 * 60_000 });
}

export function useResolvedProfile(code: string, asOf: string) {
  return useQuery<ResolvedProfile>({
    queryKey: standardsKeys.resolved(code, asOf),
    queryFn: () =>
      standardsApi.getResolved({ code: code || undefined, as_of: asOf || undefined }),
  });
}

function invalidateRuleSets(qc: ReturnType<typeof useQueryClient>, id?: string) {
  void qc.invalidateQueries({ queryKey: standardsKeys.ruleSets() });
  if (id) void qc.invalidateQueries({ queryKey: standardsKeys.ruleSet(id) });
  void qc.invalidateQueries({ queryKey: [...standardsKeys.all, "resolved"] });
}

export function useCreateRuleSetDraft() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: RuleSetCreatePayload) => standardsApi.createDraft(payload), onSuccess: () => invalidateRuleSets(qc) });
}

export function useUpdateRuleSetDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: RuleSetDraftUpdatePayload) => standardsApi.updateDraft(id, payload), onSuccess: () => invalidateRuleSets(qc, id) });
}

export function useCloneRuleSet() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => standardsApi.clone(id), onSuccess: () => invalidateRuleSets(qc) });
}

export function useValidateRuleSet() {
  return useMutation({ mutationFn: (id: string) => standardsApi.validate(id) });
}

export function usePublishRuleSet() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => standardsApi.publish(id), onSuccess: (_data, id) => invalidateRuleSets(qc, id) });
}

export function useUpsertRecipe(ruleSetId: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: RecipeUpsertPayload) => standardsApi.upsertRecipe(ruleSetId, payload), onSuccess: () => invalidateRuleSets(qc, ruleSetId) });
}

export function useDeleteRecipe(ruleSetId: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (recipeId: string) => standardsApi.deleteRecipe(ruleSetId, recipeId), onSuccess: () => invalidateRuleSets(qc, ruleSetId) });
}

export function useCreateWorkItem() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (payload: WorkItemCreatePayload) => standardsApi.createWorkItem(payload), onSuccess: () => void qc.invalidateQueries({ queryKey: standardsKeys.workItems() }) });
}

export function useUpdateWorkItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: WorkItemUpdatePayload }) => standardsApi.updateWorkItem(id, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: standardsKeys.workItems() }),
  });
}
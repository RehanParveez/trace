type Num = number | string;

export type RuleSetStatus = "DRAFT" | "ACTIVE" | "SUPERSEDED" | "ARCHIVED";
export type DeductionBehavior = "DEDUCT" | "IGNORE" | "PARTIAL";
export type RecipeItemType = "MATERIAL" | "LABOUR" | "CUSTOM";
export type IssueSeverity = "error" | "warning" | "info";

export interface RuleSet {
  id: string; organization_id: string | null; code: string; name: string; description: string | null;
  jurisdiction: string | null; province: string | null; city: string | null;
  standard_name: string | null; standard_edition: string | null;
  effective_from: string | null; effective_to: string | null;
  status: RuleSetStatus; immutable_version: number; convention_code: string | null;
  is_system: boolean; published_at: string | null; content_hash: string | null;
  supersedes_rule_set_id: string | null; wall_measurement_method: string;
  net_vs_gross_preference: string; preferred_units: Record<string, unknown>; extra_config: Record<string, unknown>;
}

export interface OpeningRule {
  element_scope: string; lower_area_m2: Num; upper_area_m2: Num | null;
  deduction_behavior: DeductionBehavior; deduction_fraction: Num | null;
  edge_behavior: string | null; extra_config: Record<string, unknown>;
}

export interface WastageRule {
  material_class: string; procurement_stage: string; factor: Num;
  unit: string | null; justification: string | null;
}

export interface ReinforcementRule {
  element_scope: string; bar_role: string; lap_basis: string | null; lap_coefficient: Num | null;
  hook_rules: Record<string, unknown>; bend_rules: Record<string, unknown>;
  dev_length_method: string | null; splice_constraints: Record<string, unknown>; extra_config: Record<string, unknown>;
}

export interface ElementMapping {
  ifc_type: string; work_item_code: string | null; default_category: string | null;
  quantity_source_preference: string; unit_override: string | null; confidence_base: Num;
  extra_mapping: Record<string, unknown>;
}

export interface RecipeComponent {
  sequence: number; work_item_code: string | null; description_template: string; unit: string;
  quantity_formula_code: string; output_unit: string; category: string | null;
  item_type: RecipeItemType; is_optional: boolean;
}

export interface Recipe {
  id: string; code: string; name: string; description: string | null;
  trigger_ifc_types: string[]; trigger_conditions: Record<string, unknown>;
  is_active: boolean; components: RecipeComponent[];
}

export interface RuleSetDetail {
  rule_set: RuleSet; opening_rules: OpeningRule[]; wastage_rules: WastageRule[];
  reinforcement_rules: ReinforcementRule[]; mappings: ElementMapping[]; recipes: Recipe[];
}

export interface ValidationIssue { code: string; severity: IssueSeverity; message: string; ref: string | null }
export interface ValidationResult { valid: boolean; issues: ValidationIssue[] }
export interface PublishResult { rule_set: RuleSet; warnings: ValidationIssue[] }

export interface WorkItem {
  id: string; organization_id: string | null; code: string; description: string; unit: string;
  trade: string | null; wbs_code: string | null; specification: string | null; csr_ref: string | null;
  default_formula_code: string | null; is_system: boolean; is_active: boolean; extra: Record<string, unknown>;
}

export interface Formula { code: string; output_unit: string; description: string; input_unit: string | null; needs_kernel: boolean }
export interface Convention { id: string; code: string; name: string; description: string | null; conserves_volume: boolean; parameters: Record<string, unknown> }

export interface ResolvedProfile {
  rule_set_id: string; code: string; immutable_version: number; content_hash: string | null;
  convention_code: string | null; conserves_volume: boolean;
  jurisdiction: string | null; province: string | null; standard_name: string | null; standard_edition: string | null;
  wall_measurement_method: string; net_vs_gross_preference: string;
  preferred_units: Record<string, unknown>; tolerances: Record<string, unknown>;
  opening_rules: Array<{ element_scope: string; lower_area_m2: Num; upper_area_m2: Num | null; behavior: DeductionBehavior; fraction: Num | null; edge_behavior: string | null }>;
  wastage_rules: Array<{ material_class: string; procurement_stage: string; factor: Num }>;
  reinforcement_rules: Array<Record<string, unknown>>;
  mappings: Array<{ ifc_type: string; work_item_code: string | null; default_category: string | null; quantity_source_preference: string; unit_override: string | null; confidence_base: Num; material_class: string | null }>;
  recipes: Array<{
    id: string; code: string; name: string; trigger_ifc_types: string[]; trigger_conditions: Record<string, unknown>;
    components: Array<{ sequence: number; work_item_code: string | null; description_template: string; unit: string; formula_code: string; category: string | null; item_type: string; is_optional: boolean; material_class: string | null }>;
  }>;
}

export interface RuleSetCreatePayload {
  code: string; name: string; description?: string | null; jurisdiction?: string | null; province?: string | null;
  city?: string | null; standard_name?: string | null; standard_edition?: string | null;
  effective_from?: string | null; effective_to?: string | null; convention_code?: string | null;
}

export interface RuleSetDraftUpdatePayload {
  name?: string; description?: string; standard_edition?: string; effective_from?: string; effective_to?: string;
  convention_code?: string; wall_measurement_method?: string; net_vs_gross_preference?: "net" | "gross";
  opening_rules?: OpeningRule[]; wastage_rules?: WastageRule[]; reinforcement_rules?: ReinforcementRule[]; mappings?: ElementMapping[];
}

export interface RecipeUpsertPayload {
  code: string; name: string; description?: string | null; trigger_ifc_types: string[];
  trigger_conditions?: Record<string, unknown>;
  components: Array<{
    sequence: number; work_item_code: string | null; description_template: string; unit: string;
    quantity_formula_code: string; category?: string | null; item_type: RecipeItemType; is_optional: boolean;
  }>;
}

export interface WorkItemCreatePayload {
  code: string; description: string; unit: string; trade?: string | null; wbs_code?: string | null;
  default_formula_code?: string | null; extra?: Record<string, unknown>;
}

export interface WorkItemUpdatePayload {
  description?: string; trade?: string | null; wbs_code?: string | null;
  default_formula_code?: string | null; is_active?: boolean; extra?: Record<string, unknown>;
}
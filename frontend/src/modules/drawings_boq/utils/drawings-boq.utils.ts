import type {BOQLifecycle, BOQItemStatus, BOQItemType, BOQVersionStatus, CalculationRunStatus, DrawingStatus, ReviewSeverity,
  AdjustmentResponse, EngineBlocks, EngineSeverity, ReviewIssueResponse, ScheduleImportStatus, ScheduleKind, ScheduleRowResponse, Surface, TraceStep, DrawingElement, ElementPlacement
} from "../types/drawings-boq.types";

export interface WarningInfo {
  severity: EngineSeverity;
  blocks: EngineBlocks;
  message: string;
  fix: string | null;
}

export const LOW_CONFIDENCE_THRESHOLD = 0.6;

export const WORKING_LIFECYCLES: readonly BOQLifecycle[] = [
  "DRAFT",
  "CALCULATING",
  "CALCULATED",
  "UNDER_REVIEW",
];

export const ACTIVE_RUN_STATUSES: readonly CalculationRunStatus[] = [
  "QUEUED",
  "RUNNING",
  "STAGED",
  "PROMOTED",
];

export const RUN_SOFT_LIMIT_MS = 1_500_000;

export const NON_WAIVABLE_CODES = new Set([
  "NON_CONSERVING_ALLOCATION",
  "UNALLOCATED_OVERLAP",
]);

export const REVIEW_WARNING_CODES = new Set([
  "GEOMETRY_INCOMPLETE",
  "QTO_FALLBACK",
  "LOW_CONFIDENCE_GEOMETRY",
  "UNSUPPORTED_GEOMETRY",
  "QTO_GEOMETRY_MISMATCH",
  "ALLOCATION_APPROXIMATE",
  "NOT_ALLOCATED",
  "OVER_DEDUCTED",
  "ZERO_NET_QUANTITY",
  "SAME_ROLE_OVERLAP",
  "OPENING_SIZE_MISSING",
  "OPENING_ASSIGNMENT_APPROXIMATE",
  "FINISH_NEEDS_REVIEW",
  "STEEL_ESTIMATED",
  "DECLARED_WEIGHT_MISMATCH",
  "MIXED_GRADES",
  "LAP_LENGTH_UNKNOWN",
  "MATCHED_ELEMENT_NOT_MEASURED",
  "DUPLICATE_SOLID",
  "SCHEDULE_OVERLAPS_MODEL",
  "SCHEDULE_LOW_CONFIDENCE",
]);

export const isRunActive = (
  status: CalculationRunStatus | undefined,
): boolean =>
  !!status && ACTIVE_RUN_STATUSES.includes(status);

export const isVersionMutable = (
  lifecycle: BOQLifecycle | undefined,
): boolean =>
  !!lifecycle && WORKING_LIFECYCLES.includes(lifecycle);

export const isLowConfidence = (
  confidence: number | string | null | undefined,
): boolean =>
  confidence !== null &&
  confidence !== undefined &&
  Number(confidence) < LOW_CONFIDENCE_THRESHOLD;

export const isWaivable = (code: string): boolean =>
  !NON_WAIVABLE_CODES.has(code);

export const LEDGER_WARNING_CATALOG: Record<string, WarningInfo> = {
  OPENINGS_NOT_DEDUCTED: {
    severity: "info",
    blocks: "NONE",
    message: "Wall volume is gross of openings: no hosted openings were found for this wall.",
    fix: "Check that doors and windows are hosted by this wall, or add an adjustment.",
  },

  SPEC_MIX_MISSING: {
    severity: "info", blocks: "NONE",
    message: "The model does not state a concrete mix or grade for these elements, so they are grouped without one.",
    fix: "Give the concrete a material name that carries the mix (for example Reinforced Concrete 1:2:4 or M20), or confirm the mix with the engineer.",
  },

  SPEC_MORTAR_MISSING: {
    severity: "info", blocks: "NONE",
    message: "The model does not state a mortar ratio for these masonry walls, so they are grouped without one.",
    fix: "Read the mortar ratio from the drawing notes or specification and set it on the rule set or the wall material.",
  },

  SPEC_THICKNESS_MISSING: {
    severity: "warning", blocks: "NONE",
    message: "The model does not give a thickness for these masonry walls, so walls of different thickness may be grouped together.",
    fix: "Give the walls a thickness in the model, or check them one by one.",
  },

  DATUM_DEFAULTED: {
    severity: "info", blocks: "NONE",
    message: "The stage this quantity falls in depends on a reference level the model does not give (the DPC or the lintel level), so an assumed level was used. The total quantity is not affected.",
    fix: "Set the DPC drop below floor level or the lintel height on the measurement convention, or confirm the levels with the engineer.",
  },

  SPACE_OVER_DEDUCTED: {
    severity: "error", blocks: "APPROVAL",
    message: "The parts of the drawing that overlap this member took more than its own volume, so what was taken off was scaled down to fit. The total is kept, but which member the overlap belongs to is uncertain.",
    fix: "Check the views of this member for a duplicate mark or a view placed on top of another, then calculate again.",
  },

  SPACE_VIEW_NOT_PLACED: {
    severity: "warning", blocks: "NONE",
    message: "The drawing view this member was measured on has no placement on the building, so it was only compared with members of its own view.",
    fix: "Open the frame view of the drawing and confirm the placement of this view, then calculate again.",
  },

  SPACE_NO_HEIGHT: {
    severity: "warning", blocks: "NONE",
    message: "The height range of this member is not known (its floor has no level, or the lintel head or footing level is not given), so it could not be compared with other members or placed in a stage of work.",
    fix: "Give the floor levels, the lintel head or the footing level, then calculate again.",
  },

  SPACE_SAME_ROLE_OVERLAP: {
    severity: "warning", blocks: "NONE",
    message: "Two measurements of the same kind of member lie over each other on the drawing, so the shared part was counted once.",
    fix: "Check that the same wall or beam was not measured twice.",
  },

  STAGE_DATUM_DEFAULTED: {
    severity: "info", blocks: "NONE",
    message: "The stage this quantity falls in depends on a reference level the drawing does not give (the DPC or the lintel level), so an assumed level was used. The total quantity is not affected, only which stage it is shown under.",
    fix: "Set the DPC drop below floor level or the lintel height on the measurement convention, or confirm the levels with the engineer.",
  },

  STAGE_NOT_SPLIT: {
    severity: "warning", blocks: "NONE",
    message: "This element stands across a stage level but could not be cut there, so all of it was put in the stage holding its middle.",
    fix: "Check the element in the model; re-upload with the current reader so footprints are stored.",
  },

  STAGE_UNRESOLVED: {
    severity: "warning", blocks: "NONE",
    message: "The height of this element is not known, so it could not be placed in a stage of work.",
    fix: "Check the element in the model.",
  },

  STAGE_DEDUCTION_APPORTIONED: {
    severity: "info", blocks: "NONE",
    message: "A deduction on this element has no recorded height, so it was shared between the stages in proportion to their height.",
    fix: "Re-run with the current reader so openings carry their heights.",
  },

  ZERO_GROSS_VOLUME: {
    severity: "warning",
    blocks: "NONE",
    message: "Gross volume rounds to zero; the element was not measured.",
    fix: "Check profile and extrusion depth in the model.",
  },

  QTO_GEOMETRY_MISMATCH: {
    severity: "warning", blocks: "NONE",
    message: "Geometry volume differs from the model's Qto volume by more than 2%.",
    fix: "Check the element in the model; the geometry volume was used.",
  },

  DECLARED_WEIGHT_MISMATCH: {
    severity: "warning", blocks: "NONE",
    message: "Computed bar weight differs from the weight declared in the schedule beyond tolerance.",
    fix: "Check bar dimensions, count and shape code in the bar schedule.",
  },

  MATCHED_ELEMENT_NOT_MEASURED: {
    severity: "warning", blocks: "NONE",
    message: "Schedule row is matched to an element that was not measured; steel is held separately.",
    fix: "Check the matched element's geometry and role.",
  },

  UNIT_WEIGHT_COMPUTED: {
    severity: "info", blocks: "NONE",
    message: "No bar size in the table; unit weight computed as d²/162.2.",
    fix: "Add this bar size to the bar size table.",
  },

  MIXED_GRADES: {
    severity: "warning", blocks: "NONE",
    message: "Bar marks on this element use different steel grades.",
    fix: null,
  },

  LAP_LENGTH_UNKNOWN: {
    severity: "warning", blocks: "NONE",
    message: "Bars exceed stock length but no lap rule applies; laps were not added.",
    fix: "Add a lap rule for this element scope to the rule set.",
  },

  SAME_ROLE_OVERLAP: {
    severity: "warning",
    blocks: "NONE",
    message: "Elements of the same role overlap; the lowest element id owns the shared volume.",
    fix: "Check these overlaps in the model.",
  },

  STEEL_ESTIMATED: {
    severity: "warning", blocks: "ISSUE",
    message: "Steel is estimated from a kg/m³ rule, not a bar schedule.",
    fix: "Import a bar bending schedule to replace the estimate.",
  },

  ALLOCATION_APPROXIMATE: {
    severity: "warning",
    blocks: "NONE",
    message: "Overlaps were allocated from bounding boxes, not exact footprints.",
    fix: "Re-upload the model with the current reader so footprints are stored.",
  },

  NOT_ALLOCATED: {
    severity: "warning",
    blocks: "NONE",
    message: "Elements were not allocated (no usable footprint, sloped or non-prismatic shape, a role the convention does not rank, or no convention on the rule set); their volume is gross and may overlap other elements.",
    fix: "Check these elements in the model, or set a convention on the rule set.",
  },

  DUPLICATE_SOLID: {
    severity: "warning",
    blocks: "NONE",
    message: "An element is fully inside another element of the same role (duplicate in the model); it was given zero volume.",
    fix: "Delete the duplicate element in the model.",
  },

  SCHEDULE_OVERLAPS_MODEL: {
    severity: "warning",
    blocks: "APPROVAL",
    message: "A schedule row uses a work item that the model or the finish rules already measured in this run, so the quantity may be counted twice.",
    fix: "Archive the schedule row, change its work item, or waive this issue with a reason.",
  },

  SCHEDULE_LOW_CONFIDENCE: {
    severity: "warning",
    blocks: "NONE",
    message: "A schedule row was read with low confidence.",
    fix: "Check the row against the drawing.",
  },

  QTO_FALLBACK: {
    severity: "warning",
    blocks: "NONE",
    message: "Volume was taken from the model's Qto value because geometry was incomplete.",
    fix: null,
  },

  LOW_CONFIDENCE_GEOMETRY: {
    severity: "warning",
    blocks: "NONE",
    message: "Volume is approximate (bounding box or Qto only).",
    fix: null,
  },

  GEOMETRY_INCOMPLETE: {
    severity: "warning",
    blocks: "NONE",
    message: "Profile or depth missing; no volume was measured.",
    fix: null,
  },

  UNSUPPORTED_GEOMETRY: {
    severity: "warning",
    blocks: "NONE",
    message: "Geometry could not be measured.",
    fix: null,
  },

  ZERO_NET_QUANTITY: {
    severity: "warning",
    blocks: "NONE",
    message: "Net quantity became zero after allocation.",
    fix: null,
  },

  OPENING_SIZE_MISSING: {
    severity: "warning",
    blocks: "NONE",
    message: "An opening has no usable size, so it was not deducted.",
    fix: "Add width and height to the door or window in the model.",
  },

  OPENING_ASSIGNMENT_APPROXIMATE: {
    severity: "warning",
    blocks: "NONE",
    message: "Openings were assigned to rooms by wall membership, without a position check.",
    fix: "Check the deducted openings in the measurement book.",
  },

  FINISH_NEEDS_REVIEW: {
    severity: "warning",
    blocks: "NONE",
    message: "The finish for this surface needs review.",
    fix: null,
  },

    LAYER_FINISH_EXCLUDED: {
    severity: "info", blocks: "NONE",
    message: "The wall is built up of layers in the model. The plaster, paint and other finish layers were taken out of the masonry volume, so the brickwork is measured at its own thickness only.",
    fix: "Nothing to do. Plaster and paint are measured separately from the room finishes.",
  },

  LAYER_UNPRICED: {
    severity: "warning", blocks: "NONE",
    message: "A layer of this element (for example insulation, a membrane or a cavity) has no work item, so it is not in the BOQ. The element's volume was reduced by it.",
    fix: "Map this layer family to a work item on the rule set (a mapping named LAYER:<FAMILY>), or confirm it is not to be billed.",
  },

  LAYER_THICKNESS_MISMATCH: {
    severity: "warning", blocks: "NONE",
    message: "The layers of this element add up to a different thickness from the element's own width in the model. The layers were scaled to the element's volume.",
    fix: "Check the layer thicknesses in the model.",
  },

  LAYER_NOT_SPLIT: {
    severity: "warning", blocks: "NONE",
    message: "None of this element's layers could be matched to a billable work item, so the element was left whole as one material.",
    fix: "Check the material layers of this element in the model, or map the layer families to work items on the rule set.",
  },

  MATERIAL_GENERIC: {
    severity: "warning", blocks: "NONE",
    message: "The model gives this element no real material (it says generic, default or nothing), so the grade or mortar could not be read and the masonry or concrete class is a guess.",
    fix: "Give the element a material in the model, for example Brick or Concrete C25.",
  },

  DERIVED_ASSUMED: {
    severity: "warning", blocks: "NONE",
    message: "This quantity is not drawn in the model. It is worked out from the foundation using site assumptions that were not given (working space, PCC projection or PCC thickness), so standard values were used.",
    fix: "Confirm the working space, PCC projection and PCC thickness for this site when starting the run.",
  },

  DERIVED_NGL_ASSUMED: {
    severity: "warning", blocks: "NONE",
    message: "The natural ground level is not in the model, so the excavation and backfill depth was worked out from an assumed level below the floor level.",
    fix: "Give the natural ground level (how far below floor level) when starting the run.",
  },

  DERIVED_BOX_FOOTPRINT: {
    severity: "warning", blocks: "NONE",
    message: "The foundation has no exact outline in the model, so its bounding rectangle was used for the excavation and PCC. A foundation that is not rectangular is overstated.",
    fix: "Re-upload the model with the current reader so outlines are stored.",
  },

  DERIVED_MARK_POSITION: {
    severity: "warning", blocks: "NONE",
    message: "This footing was read from a drawing, so it is placed at its mark with the size from the schedule or the drawing, not at a drawn outline. Footings close together may share a trench in the drawing, and the shared part is only approximate here.",
    fix: "Check the excavation, PCC and backfill of these footings against the foundation plan, or measure the trench by hand.",
  },

  OVER_DEDUCTED: {
    severity: "error",
    blocks: "APPROVAL",
    message: "Deductions exceeded the gross volume; the quantity was clamped to zero.",
    fix: "Report this model; the allocation is inconsistent.",
  },
};

export const warningInfo = (code: string): WarningInfo =>
  LEDGER_WARNING_CATALOG[code] ?? {
    severity: "warning",
    blocks: "NONE",
    message: `Ledger warning ${code}.`,
    fix: null,
  };

export const UNIT_TABLE: Record<
  string,
  { canonical: string; factor: number }
> = {
  m3: { canonical: "m3", factor: 1 },
  cft: { canonical: "m3", factor: 35.3146667 },
  m2: { canonical: "m2", factor: 1 },
  sft: { canonical: "m2", factor: 10.7639104 },
  m: { canonical: "m", factor: 1 },
  rft: { canonical: "m", factor: 3.280839895 },
  kg: { canonical: "kg", factor: 1 },
  nos: { canonical: "nos", factor: 1 },
};

export const activeAdjustments = <
  T extends { revoked_at: string | null },
>(
  rows: T[],
): T[] => rows.filter((row) => !row.revoked_at);

const SEVERITY_RANK: Record<string, number> = {
  error: 0,
  warning: 1,
  info: 2,
};

export const severityRank = (severity: string): number =>
  SEVERITY_RANK[severity] ?? 3;

export const FORMULA_UNIT: Record<string, string> = {
  SOLID_NET_VOLUME: "m3", OPENING_COUNT: "nos",
  FINISH_FLOOR_AREA: "m2", FINISH_CEILING_AREA: "m2",
  FINISH_WALL_AREA_NET: "m2", FINISH_DADO_AREA_NET: "m2",
  FINISH_SKIRTING_LENGTH_NET: "m",
  SCHEDULE_LINE_M3: "m3", SCHEDULE_LINE_M2: "m2", SCHEDULE_LINE_M: "m",
  SCHEDULE_LINE_KG: "kg", SCHEDULE_LINE_NOS: "nos",
  REBAR_BBS_WEIGHT: "kg", REBAR_RULE_ESTIMATE: "kg",
};

export const DEDUCTION_RULE_LABEL: Record<string, string> = {
  OPENING_DEDUCT: "Opening deducted",
  OPENING_PARTIAL: "Opening partly deducted",
  OPENING_IGNORED: "Opening below threshold",
  OPENING_SIZE_MISSING: "Opening size missing",
};

export const TRACE_OP_LABEL: Record<string, string> = {
  gross_volume: "Gross volume", stage_gross_volume: "Gross volume in this stage", deduction: "Deduction", net_volume: "Net volume",
  gross_area: "Gross area", gross_length: "Gross length", net: "Net", count: "Count",
  schedule_quantity: "Schedule quantity", declared_cut_length: "Declared cut length",
  segments: "Segment total", bend_deduction: "Bend deduction", hook_allowance: "Hook allowance",
  laps: "Laps", weight: "Weight", declared_weight: "Declared weight",
  bar_mark: "Bar mark", intensity: "Steel intensity",
};

export function formatDrawingStatus(
  status: DrawingStatus,
): string {
  switch (status) {
    case "UPLOADED":
      return "Uploaded";
    case "PROCESSING":
      return "Processing";
    case "PARSED":
      return "Parsed";
    case "FAILED":
      return "Failed";
    default:
      return status;
  }
}

export function getDrawingStatusTone(
  status: DrawingStatus,
): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "PARSED":
      return "green";
    case "PROCESSING":
      return "gold";
    case "UPLOADED":
      return "blue";
    case "FAILED":
      return "red";
    default:
      return "slate";
  }
}

export function isDrawingInProgress(
  status: DrawingStatus,
): boolean {
  return (
    status === "UPLOADED" ||
    status === "PROCESSING"
  );
}

export function formatBOQItemStatus(
  status: BOQItemStatus,
): string {
  return status === "APPROVED"
    ? "Approved"
    : "Draft";
}

export function formatBOQLifecycle(
  lifecycle: BOQLifecycle | null | undefined,
): string {
  if (!lifecycle) {
    return "Draft";
  }
  return lifecycle
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase(),
    );
}

export function getBOQLifecycleTone(
  lifecycle: BOQLifecycle | null | undefined,
): "green" | "gold" | "red" | "slate" | "blue" {
  switch (lifecycle) {
    case "APPROVED":
    case "ISSUED":
      return "green";
    case "UNDER_REVIEW":
      return "gold";
    case "CALCULATING":
      return "blue";
    case "SUPERSEDED":
    case "ARCHIVED":
      return "slate";
    default:
      return "slate";
  }
}

export function formatCalculationRunStatus(
  status: CalculationRunStatus,
): string {
  return status
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase(),
    );
}

export function getCalculationRunTone(
  status: CalculationRunStatus,
): "green" | "gold" | "red" | "slate" | "blue" {
  switch (status) {
    case "COMPLETED":
    case "PROMOTED":
      return "green";
    case "RUNNING":
    case "STAGED":
      return "blue";
    case "QUEUED":
      return "gold";
    case "FAILED":
    case "CANCELLED":
      return "red";
    default:
      return "slate";
  }
}

export function formatReviewSeverity(
  severity: ReviewSeverity,
): string {
  return severity.toUpperCase();
}

export function formatFileSize(
  bytes: number,
): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 ** 2) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  if (bytes < 1024 ** 3) {
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  }
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

export function formatQuantity(
  value: number | string,
): string {
  const num = Number(value);

  return Number.isNaN(num)
    ? "—"
    : num.toLocaleString("en-PK", {
        maximumFractionDigits: 4,
      });
}

export function formatCurrency(
  value: number | string | null,
): string {
  if (value === null) {
    return "—";
  }

  const num = Number(value);

  if (Number.isNaN(num)) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-PK",
    {
      style: "currency",
      currency: "PKR",
      maximumFractionDigits: 2,
    },
  ).format(num);
}

export function computeLineTotal(
  quantity: number | string,
  unitRate: number | string | null,
): number | null {
  if (unitRate === null) {
    return null;
  }

  const q = Number(quantity);
  const r = Number(unitRate);

  return Number.isNaN(q) ||
    Number.isNaN(r)
    ? null
    : q * r;
}

export function formatBOQItemType(
  type: BOQItemType,
): string {
  switch (type) {
    case "MATERIAL":
      return "Material";
    case "LABOUR":
      return "Labour";
    case "CUSTOM":
      return "Additional";
    default:
      return type;
  }
}

export function formatBOQVersionStatus(
  status: BOQVersionStatus,
): string {
  return status === "ACTIVE"
    ? "Active"
    : "Superseded";
}

export function triggerBlobDownload(
  blob: Blob,
  filename: string,
): void {
  const url =
    window.URL.createObjectURL(blob);
  const link =
    document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function openBlobInNewTab(
  blob: Blob,
): void {
  const url =
    window.URL.createObjectURL(blob);
  window.open(
    url,
    "_blank",
    "noopener,noreferrer",
  );
  window.setTimeout(
    () => window.URL.revokeObjectURL(url),
    60_000,
  );
}

export function formatDateTime(
  value: string | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-PK");
}

export function formatJsonValue(
  value: unknown,
): string {
  if (value === null ||
      value === undefined) {
    return "—";
  }

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  try {
    return JSON.stringify(
      value,
      null,
      2,
    );
  } catch {
    return String(value);
  }
}

export function roundHalfUp(
  value: number,
  places: number,
): number {
  const multiplier = 10 ** places;

  return (
    Math.sign(value) *
    Math.round(
      Math.abs(value) * multiplier + Number.EPSILON,
    )
  ) / multiplier;
}

export function compatibleUnits(unit: string): string[] {
  const entry = UNIT_TABLE[
    unit.trim().toLowerCase()
  ];

  if (!entry) {
    return [unit];
  }

  return Object.entries(UNIT_TABLE)
    .filter(([, value]) => value.canonical === entry.canonical)
    .map(([key]) => key);
}

export function convertRate(
  rate: number,
  fromUnit: string,
  toUnit: string,
): number | null {
  const from = UNIT_TABLE[
    (fromUnit || "").trim().toLowerCase()
  ];

  const to = UNIT_TABLE[
    (toUnit || "").trim().toLowerCase()
  ];

  if (!from || !to || from.canonical !== to.canonical) {
    return null;
  }

  return roundHalfUp(
    (rate * from.factor) / to.factor,
    2,
  );
}

export function computeQuantity(
  net: number | string,
  adjustments: Pick<
    AdjustmentResponse,
    "kind" | "value"
  >[],
): number {
  let base = Number(net);
  let delta = 0;

  for (const adjustment of adjustments) {
    if (adjustment.kind === "REPLACE") {
      base = Number(adjustment.value);
    } else {
      delta += Number(adjustment.value);
    }
  }

  return roundHalfUp(base + delta, 4);
}

export function sortIssues(
  issues: ReviewIssueResponse[],
): ReviewIssueResponse[] {
  return [...issues].sort(
    (a, b) =>
      severityRank(a.severity) - severityRank(b.severity) ||
      a.code.localeCompare(b.code),
  );
}

export function countBlocking(
  issues: Pick<
    ReviewIssueResponse,
    "status" | "blocks"
  >[],
): {
  approval: number;
  issue: number;
} {
  const open = issues.filter(
    (issue) => issue.status === "OPEN",
  );

  return {
    approval: open.filter(
      (issue) => issue.blocks === "APPROVAL",
    ).length,

    issue: open.filter(
      (issue) => issue.blocks === "ISSUE",
    ).length,
  };
}

export function formatPrecise(
  value: number | string | null | undefined,
  maxDigits = 4,
): string {
  if (value === null || value === undefined) {
    return "—";
  }

  const numberValue = Number(value);

  return Number.isNaN(numberValue)
    ? "—"
    : numberValue.toLocaleString("en-PK", {
        maximumFractionDigits: maxDigits,
      });
}

export function scoreTone(
  score: number | string,
): "green" | "gold" | "red" {
  const value = Number(score);

  return value >= 90
    ? "green"
    : value >= 60
      ? "gold"
      : "red";
}

export function runTone(
  status: CalculationRunStatus,
): "green" | "gold" | "red" | "blue" | "slate" {
  if (status === "COMPLETED") {
    return "green";
  }
  if (status === "FAILED") {
    return "red";
  }
  if (
    status === "CANCELLED" ||
    status === "SUPERSEDED"
  ) {
    return "slate";
  }
  if (status === "QUEUED") {
    return "blue";
  }

  return "gold";
}

export function lifecycleTone(
  lifecycle: BOQLifecycle,
): "green" | "gold" | "red" | "blue" | "slate" {
  switch (lifecycle) {
    case "APPROVED":
    case "ISSUED":
      return "green";

    case "UNDER_REVIEW":
    case "CALCULATING":
      return "gold";

    case "CALCULATED":
      return "blue";

    default:
      return "slate";
  }
}

const STAGE_FALLBACK: Record<string, string> = {
  BELOW_PLINTH: "Below plinth",
  PLINTH_TO_LINTEL: "Plinth to lintel",
  LINTEL_TO_SLAB: "Lintel to slab",
  TOP: "Above roof slab",
  PARAPET: "Roof parapet",
  MUMTY: "Mumty and above",
};

export function stageDescriptor(code: string): { key: string; fallback: string; n?: number } {
  const m = /^UPPER_FLOOR_(\d+)$/.exec(code);
  if (m) return { key: "boq.stage.UPPER_FLOOR", fallback: `Upper floor ${m[1]}`, n: Number(m[1]) };
  return { key: `boq.stage.${code}`, fallback: STAGE_FALLBACK[code] ?? code.replace(/_/g, " ").toLowerCase() };
}

export function stageSortKey(code: string | null | undefined): number {
  if (!code) return 999;
  const order = ["BELOW_PLINTH", "PLINTH_TO_LINTEL", "LINTEL_TO_SLAB"].indexOf(code);
  if (order >= 0) return order;
  const m = /^UPPER_FLOOR_(\d+)$/.exec(code);
  if (m) return 10 + Number(m[1]);
  if (code === "PARAPET") return 890;
  if (code === "MUMTY") return 895;
  return code === "TOP" ? 900 : 500;
}

export function traceStepValue(step: TraceStep): { value: string; unit: string } | null {
  for (const unit of ["m3", "m2", "kg", "nos", "m", "mm"]) {
    const v = step[unit];
    if (typeof v === "string" || typeof v === "number") return { value: String(v), unit };
  }
  return null;
}

export type MeasureMode = "EXACT" | "APPROXIMATE" | "NONE";

export function traceStepDetail(step: TraceStep): string {
  const used = traceStepValue(step)?.unit;
  return Object.entries(step)
    .filter(([k, v]) => k !== "op" && k !== used && v !== null && v !== undefined && v !== "")
    .map(([k, v]) => {
      const s = typeof v === "object" ? JSON.stringify(v) : String(v);
      return `${k.replace(/_/g, " ")}: ${k.endsWith("_id") ? s.slice(0, 8) : s}`;
    })
    .join(" · ");
}

export function elementMeasureMode(el: DrawingElement): MeasureMode | null {
  const b = [el.bbox_min_x_mm, el.bbox_min_y_mm, el.bbox_min_z_mm,
    el.bbox_max_x_mm, el.bbox_max_y_mm, el.bbox_max_z_mm];
  if (el.placement === undefined && b.every((v) => v === undefined)) return null;
  const pl = (el.placement ?? {}) as ElementPlacement;
  if ((pl.plan_mm?.length ?? 0) >= 3 && pl.z_min_mm != null && pl.z_max_mm != null) return "EXACT";
  return b.every((v) => v != null) ? "APPROXIMATE" : "NONE";
}

export const isRebarProvenanceEstimate = (p: string) => p === "RULE_ESTIMATE";

export const SURFACES: readonly Surface[] = ["FLOOR", "WALL", "CEILING", "SKIRTING", "DADO"];

export const SURFACE_UNIT: Record<Surface, "m2" | "m"> = {
  FLOOR: "m2",
  WALL: "m2",
  CEILING: "m2",
  DADO: "m2",
  SKIRTING: "m",
};

export const SCHEDULE_KINDS: readonly ScheduleKind[] = ["DOOR", "WINDOW", "FINISH", "FIXTURE", "GENERAL"];

export const KIND_DEFAULT_WORK_ITEM: Partial<Record<ScheduleKind, string>> = {
  DOOR: "DOR-NOS",
  WINDOW: "WIN-NOS",
};

export const WORK_ITEM_SUGGESTIONS = [
  "DOR-NOS",
  "WIN-NOS",
  "FIN-FLOOR",
  "FIN-SKIRT",
  "FIN-DADO",
  "FIN-CEIL-PAINT",
  "FIN-CEIL-PLASTER",
  "FIN-PAINT",
  "FIN-PLASTER",
];

export const ROW_CONFIDENCE_REVIEW = 0.6;
export const SCHEDULE_FILE_MAX_BYTES = 5 * 1024 * 1024;
export const SCHEDULE_FILE_EXTENSIONS = [".csv", ".txt", ".xlsx"];

export const SPACE_CATEGORIES = [
  "TOILET", "BATHROOM", "KITCHEN", "BEDROOM", "DRESSING", "LIVING", "DINING", "CORRIDOR", "STAIR", "LIFT", "STORE", "GARAGE",
  "PARKING", "BALCONY", "TERRACE", "ROOF", "PORCH", "COURTYARD", "LAUNDRY", "SERVANT_QUARTER", "DRIVER_QUARTER", "GUARD_ROOM",
  "OFFICE", "PRAYER", "LIBRARY", "PLAYROOM", "RECREATION", "GYM", "NURSERY", "MUMTY", "SHAFT", "DUCT", "MECHANICAL", "ELECTRICAL",
  "PLUMBING", "FIRE_CONTROL", "REFUSE", "COLD_STORAGE", "BASEMENT", "ATTIC", "PLANT", "RECEPTION", "WAITING", "CLASSROOM",
  "LABORATORY", "RETAIL", "RESTAURANT", "WAREHOUSE", "WORKSHOP", "LOADING", "SERVICE", "OPEN_AREA", "UNKNOWN",
] as const;
export const EXTERNAL_CATEGORIES = new Set(["BALCONY", "TERRACE", "PORCH", "COURTYARD", "ROOF", "OPEN_AREA"]);

export const BOUNDARY_ROLE_PREFIXES = ["WALL", "CURTAIN_WALL", "DOOR", "WINDOW", "COLUMN"];

export const isBoundaryRole = (role: string | null) =>
  !!role && BOUNDARY_ROLE_PREFIXES.some((p) => role === p || role.startsWith(`${p}_`));

const MM2_PER_M2 = 1_000_000;
export const mm2ToM2 = (v: number | string | null | undefined): number | null =>
  v === null || v === undefined ? null : Number(v) / MM2_PER_M2;
export const mmToM = (v: number | string | null | undefined): number | null =>
  v === null || v === undefined ? null : Number(v) / 1000;
export const toInput = (v: number | null, digits = 4): string =>
  v === null || Number.isNaN(v) ? "" : String(+v.toFixed(digits));
export const fmt = (v: number | null | undefined, digits = 2): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : v.toLocaleString("en-PK", { maximumFractionDigits: digits });

export function inferSurface(text: string | null | undefined): Surface | null {
  const t = (text ?? "").toLowerCase();
  for (const [keyword, surface] of [
    ["skirt", "SKIRTING"],
    ["dado", "DADO"],
    ["ceil", "CEILING"],
    ["floor", "FLOOR"],
    ["wall", "WALL"],
  ] as const) {
    if (t.includes(keyword)) return surface;
  }
  return null;
}

export function suggestFinishWorkItem(
  surface: Surface | null | undefined,
  text: string | null | undefined,
): string | null {
  const t = (text ?? "").toLowerCase();
  if (surface === "FLOOR") return "FIN-FLOOR";
  if (surface === "SKIRTING") return "FIN-SKIRT";
  if (surface === "DADO") return "FIN-DADO";
  const paint = ["paint", "emulsion", "distemper"].some((k) => t.includes(k));
  if (surface === "CEILING") return paint ? "FIN-CEIL-PAINT" : "FIN-CEIL-PLASTER";
  if (surface === "WALL") return paint ? "FIN-PAINT" : t.includes("plaster") ? "FIN-PLASTER" : null;
  return null;
}

export const isLinkedFinish = (
  r: Pick<ScheduleRowResponse, "schedule_kind" | "space_id">,
) => r.schedule_kind === "FINISH" && r.space_id !== null;

export function rowConfirmBlocker(r: ScheduleRowResponse): string | null {
  if (!r.work_item_code) return "Choose a work item.";
  const linked = isLinkedFinish(r);
  if (linked && !(r.surface && SURFACES.includes(r.surface)))
    return "Set the surface (floor, wall, ceiling, skirting or dado).";
  if (r.canonical_unit === null || r.canonical_quantity === null)
    return "The unit or quantity is missing or not recognised.";
  if (!linked && r.canonical_unit === "nos" &&
    Number(r.canonical_quantity) !== Math.floor(Number(r.canonical_quantity))
  )
  return "Count (nos) must be a whole number.";
  if (!linked && Number(r.canonical_quantity) <= 0)
    return "The quantity must be greater than zero.";
  return null;
}

export const isImportEditable = (status: ScheduleImportStatus) =>
  status === "PENDING_REVIEW";

export function importTone(
  s: ScheduleImportStatus,
): "gold" | "green" | "red" | "slate" {
  return s === "PENDING_REVIEW"
    ? "gold"
    : s === "CONFIRMED"
      ? "green"
      : s === "REJECTED"
        ? "red"
        : "slate";
}

export function rowTone(s: string): "gold" | "green" | "red" {
  return s === "CONFIRMED" ? "green" : s === "REJECTED" ? "red" : "gold";
}

export const spaceLabel = (s: {
  number: string | null;
  name: string | null;
  id: string;
}) => [s.number, s.name].filter(Boolean).join(" · ") || s.id.slice(0, 8);

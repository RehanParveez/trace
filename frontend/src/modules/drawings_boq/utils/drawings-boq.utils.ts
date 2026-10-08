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
  gross_volume: "Gross volume", deduction: "Deduction", net_volume: "Net volume",
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

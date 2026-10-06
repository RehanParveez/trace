import type {BOQLifecycle, BOQItemStatus, BOQItemType, BOQVersionStatus, CalculationRunStatus, DrawingStatus, ReviewSeverity,
  AdjustmentResponse, EngineBlocks, EngineSeverity, ReviewIssueResponse,
} from "../types/drawings-boq.types";

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
    message: "Wall volumes are gross of door and window openings.",
    fix: "Opening deductions arrive with finishes and schedules; use an adjustment if one is needed now.",
  },

  SAME_ROLE_OVERLAP: {
    severity: "warning",
    blocks: "NONE",
    message: "Elements of the same role overlap; the lowest element id owns the shared volume.",
    fix: "Check these overlaps in the model.",
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
    message: "Elements had no footprint and were not allocated; their volume is gross.",
    fix: "Re-upload the model or fix the geometry.",
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

export interface WarningInfo {
  severity: EngineSeverity;
  blocks: EngineBlocks;
  message: string;
  fix: string | null;
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
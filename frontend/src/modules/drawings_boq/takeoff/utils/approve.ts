import type { ApproveReadyBody, ApproveReadyResult, CandidateFailure } from "../types/takeoff.types";

export const SIZE_FIELDS: Array<{ key: string; label: string }> = [
  { key: "wall_height_mm", label: "Wall height" },
  { key: "column_height_mm", label: "Column height" },
  { key: "slab_thickness_mm", label: "Slab thickness" },
  { key: "beam_depth_mm", label: "Beam depth" },
  { key: "footing_depth_mm", label: "Footing depth" },
  { key: "plinth_beam_depth_mm", label: "Plinth beam depth" },
  { key: "tie_band_depth_mm", label: "Tie band depth" },
  { key: "neck_height_mm", label: "Neck column height" },
  { key: "tank_wall_height_mm", label: "Tank wall height" },
];

export const REASON_LABEL: Record<string, string> = {
  ASSUMED: "a size was paired, defaulted or is disputed on the drawing",
  VALUE_MISSING: "a size is missing",
  WARNING: "the reader raised a warning",
  CHECK_WARNS: "a check between the readers warns about it",
  ERROR: "the reader found an error",
  NOT_MEASURABLE: "beam marks are only counted; draw the lengths by hand",
  FLOOR_SOURCE_UNDECIDED: "the floor is open on two sheets",
  ADDED_FROM_SECOND_SHEET: "only the sheet that shows every plan has it",
};

export type SizeState = { kind: "empty" } | { kind: "ok"; mm: number } | { kind: "bad" };

const NUM = "(\\d+(?:\\.\\d+)?)";
const round = (x: number) => Math.round(x * 10) / 10;

export function sizeState(text: string): SizeState {
  const s = text.trim().toLowerCase().replace(/,/g, "");
  if (!s) return { kind: "empty" };
  let m = s.match(new RegExp(`^${NUM}\\s*(mm)?$`));
  if (m) return finite(round(Number(m[1])));
  m = s.match(new RegExp(`^${NUM}\\s*(cm|m)$`));
  if (m) return finite(round(Number(m[1]) * (m[2] === "m" ? 1000 : 10)));
  m = s.match(new RegExp(`^${NUM}\\s*(?:ft|feet|foot|')\\s*(?:${NUM}\\s*(?:in|inch|inches|")?)?$`));
  if (m) return finite(round(Number(m[1]) * 304.8 + (m[2] ? Number(m[2]) * 25.4 : 0)));
  m = s.match(new RegExp(`^${NUM}\\s*(?:in|inch|inches|")$`));
  if (m) return finite(round(Number(m[1]) * 25.4));
  return { kind: "bad" };
}

function finite(mm: number): SizeState {
  return mm > 0 && mm <= 60000 ? { kind: "ok", mm } : { kind: "bad" };
}

export function typedFromInputs(inputs: Record<string, string>): { typed: Record<string, number>; bad: string[] } {
  const typed: Record<string, number> = {};
  const bad: string[] = [];
  for (const { key } of SIZE_FIELDS) {
    const state = sizeState(inputs[key] ?? "");
    if (state.kind === "ok") typed[key] = state.mm;
    else if (state.kind === "bad") bad.push(key);
  }
  return { typed, bad };
}

export interface ApproveSummary {
  calls: number;
  floors_chosen: number;
  accepted: number;
  confirmed: number;
  accept_failed: CandidateFailure[];
  failed_by_code: Record<string, number>;
  confirm_failed: Array<{ id?: string; code?: string; message?: string }>;
  already_decided: number;
  skipped_by_reason: Record<string, number>;
  remaining: number;
  confirmed_total: number;
  draft_total: number;
  stopped: "NO_PROGRESS" | "TOO_MANY_CALLS" | null;
}

export const MAX_CALLS = 60;

export function emptySummary(): ApproveSummary {
  return { calls: 0, floors_chosen: 0, accepted: 0, confirmed: 0, accept_failed: [], failed_by_code: {}, confirm_failed: [], already_decided: 0, skipped_by_reason: {},
    remaining: 0, confirmed_total: 0, draft_total: 0, stopped: null };
}

export function fold(sum: ApproveSummary, res: ApproveReadyResult): ApproveSummary {
  const by = { ...sum.failed_by_code };
  for (const [code, n] of Object.entries(res.failed_by_code ?? {})) by[code] = (by[code] ?? 0) + n;
  return {
    ...sum,
    calls: sum.calls + 1,
    floors_chosen: sum.floors_chosen + (res.floors_chosen?.length ?? 0),
    accepted: sum.accepted + res.accepted,
    confirmed: sum.confirmed + res.confirmed,
    accept_failed: [...sum.accept_failed, ...(res.accept_failed ?? [])].slice(0, 60),
    failed_by_code: by,
    confirm_failed: res.confirm_failed ?? [],
    already_decided: res.already_decided,
    skipped_by_reason: res.skipped_by_reason ?? {},
    remaining: res.remaining,
    confirmed_total: res.confirmed_total,
    draft_total: res.draft_total,
  };
}

export async function approveAll(
  call: (body: ApproveReadyBody) => Promise<ApproveReadyResult>,
  base: ApproveReadyBody,
  onProgress?: (sum: ApproveSummary) => void,
): Promise<ApproveSummary> {
  const left = new Set<string>(base.exclude_ids ?? []);
  let sum = emptySummary();
  for (;;) {
    const res = await call({ ...base, dry_run: false, exclude_ids: [...left] });
    for (const id of res.failed_ids ?? []) left.add(id);
    sum = fold(sum, res);
    onProgress?.(sum);
    if (res.remaining <= 0) return sum;
    if (res.accepted === 0 && (res.failed_ids ?? []).length === 0) return { ...sum, stopped: "NO_PROGRESS" };
    if (sum.calls >= MAX_CALLS) return { ...sum, stopped: "TOO_MANY_CALLS" };
  }
}

export function failureLines(sum: Pick<ApproveSummary, "accept_failed">, max = 5): Array<{ code: string; message: string; count: number }> {
  const groups = new Map<string, { code: string; message: string; count: number }>();
  for (const f of sum.accept_failed) {
    const key = `${f.code ?? ""}|${f.message ?? ""}`;
    const g = groups.get(key);
    if (g) g.count += 1;
    else groups.set(key, { code: f.code ?? "FAILED", message: f.message ?? "", count: 1 });
  }
  return [...groups.values()].sort((a, b) => b.count - a.count).slice(0, max);
}

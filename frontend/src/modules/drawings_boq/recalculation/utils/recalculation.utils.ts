import { getApiErrorCode, getApiErrorMessage } from "../../../identity";
import type { ExportJob, ExportJobStatus, FallbackReason, RunMode } from "../types/recalculation.types";

type Tone = "green" | "gold" | "red" | "slate" | "blue";
import type { Translate } from "./useRecalculationT";

export function formatDurationMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds - minutes * 60);
  return `${minutes} min ${rest} s`;
}

export function formatSeconds(seconds: number | null | undefined): string {
  return seconds === null || seconds === undefined ? "—" : formatDurationMs(seconds * 1000);
}

export function formatMb(mb: number | null | undefined): string {
  if (mb === null || mb === undefined) return "—";
  return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${Math.round(mb)} MB`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatShare(fraction: number | null | undefined): string {
  if (fraction === null || fraction === undefined) return "—";
  return `${Math.round(fraction * 100)}%`;
}

export function formatCount(value: unknown): string {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString() : "—";
}

export function formatWindow(seconds: number): string {
  if (seconds % 86400 === 0) return `${seconds / 86400} d`;
  if (seconds % 3600 === 0) return `${seconds / 3600} h`;
  if (seconds % 60 === 0) return `${seconds / 60} min`;
  return `${seconds} s`;
}

export function usagePercent(used: number, limit: number | null | undefined): number {
  if (!limit || limit <= 0) return 0;
  return Math.max(0, Math.min(100, (used / limit) * 100));
}

export function usageTone(percent: number): "green" | "gold" | "red" {
  return percent >= 100 ? "red" : percent >= 80 ? "gold" : "green";
}

export function runModeTone(mode: RunMode | string | undefined): Tone {
  return mode === "INCREMENTAL" ? "blue" : "slate";
}

export function budgetLabel(t: Translate, name: string): string {
  switch (name) {
    case "calculation_time":
      return t("scale.budget.calculation_time", "Calculation time");
    case "peak_memory":
      return t("scale.budget.peak_memory", "Peak memory");
    default:
      return name.replace(/_/g, " ");
  }
}

export function fallbackReasonText(t: Translate, reason: FallbackReason | string | undefined): string | null {
  switch (reason) {
    case undefined:
    case "":
      return null;
    case "NO_BASELINE":
      return t("scale.fallback.NO_BASELINE", "There was no earlier completed run to build on, so everything was calculated.");
    case "ALLOCATION_INPUTS_CHANGED":
      return t("scale.fallback.ALLOCATION_INPUTS_CHANGED", "The rule set, convention or engine changed since the earlier run, so everything was calculated again.");
    case "TOO_MANY_CHANGES":
      return t("scale.fallback.TOO_MANY_CHANGES", "Too much of the model changed for a partial update to be worthwhile, so everything was calculated again.");
    case "BASELINE_INCONSISTENT":
      return t("scale.fallback.BASELINE_INCONSISTENT", "The earlier run's saved data no longer matched the model, so everything was calculated again.");
    case "VERIFY_MISMATCH":
      return t("scale.fallback.VERIFY_MISMATCH", "The check found a difference between the partial update and a full calculation, so the full result was kept.");
    default:
      return String(reason).replace(/_/g, " ").toLowerCase();
  }
}

export interface FailureInfo {
  title: string;
  hint: string;
  retry: boolean;
}

export function runFailureInfo(t: Translate, code: string | null | undefined): FailureInfo {
  switch (code) {
    case "RUN_STALE":
      return {
        title: t("scale.failure.RUN_STALE.title", "The calculation stopped responding"),
        hint: t("scale.failure.RUN_STALE.hint", "The worker running it went away before it finished, and it could not be picked up again. Start it again."),
        retry: true,
      };
    case "RUN_ENQUEUE_LOST":
    case "RUN_ENQUEUE_FAILED":
      return {
        title: t("scale.failure.RUN_ENQUEUE_LOST.title", "The calculation never started"),
        hint: t("scale.failure.RUN_ENQUEUE_LOST.hint", "The request was saved but could not be handed to a worker. Nothing was calculated. Start it again."),
        retry: true,
      };
    case "RUN_TIME_LIMIT":
      return {
        title: t("scale.failure.RUN_TIME_LIMIT.title", "The calculation took too long"),
        hint: t("scale.failure.RUN_TIME_LIMIT.hint", "It was stopped at the time limit. Try fewer drawing revisions at once, or ask support if this model is very large."),
        retry: false,
      };
    case "INPUT_CHANGED":
      return {
        title: t("scale.failure.INPUT_CHANGED.title", "The drawings changed while it was running"),
        hint: t("scale.failure.INPUT_CHANGED.hint", "A selected revision was edited or replaced mid-run, so the result would not match the drawings. Start it again."),
        retry: true,
      };
    case "SELF_CHECK_FAILED":
      return {
        title: t("scale.failure.SELF_CHECK_FAILED.title", "The result failed its own checks"),
        hint: t("scale.failure.SELF_CHECK_FAILED.hint", "The quantities did not add up, so nothing was published. Running again will not change that; please report the run id to support."),
        retry: false,
      };
    case "RUN_FAILED":
      return {
        title: t("scale.failure.RUN_FAILED.title", "The calculation failed"),
        hint: t("scale.failure.RUN_FAILED.hint", "Something unexpected stopped it. You can start it again; if it keeps failing, report the run id to support."),
        retry: true,
      };
    default:
      return {
        title: t("scale.failure.other.title", "The calculation did not finish"),
        hint: t("scale.failure.other.hint", "See the message below."),
        retry: true,
      };
  }
}

export type StartErrorKind = "concurrency" | "rate" | "quota" | "in_progress" | "other";

export interface StartRunError {
  kind: StartErrorKind;
  code?: string;
  message: string;
  retryable: boolean;
}

function httpStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } })?.response?.status;
}

export function classifyStartError(error: unknown, fallback: string): StartRunError {
  const code = getApiErrorCode(error);
  const status = httpStatus(error);
  const message = getApiErrorMessage(error, fallback);
  if (code === "RUN_CONCURRENCY_LIMIT") return { kind: "concurrency", code, message, retryable: true };
  if (code === "RUN_RATE_LIMITED") return { kind: "rate", code, message, retryable: true };
  if (code === "RUN_IN_PROGRESS" || (status === 409 && !code)) return { kind: "in_progress", code, message, retryable: true };
  if (status === 402) return { kind: "quota", code, message, retryable: false };
  return { kind: "other", code, message, retryable: false };
}

export function isExportJobActive(status: ExportJobStatus | string | undefined): boolean {
  return status === "QUEUED" || status === "RUNNING";
}

export function exportJobTone(status: ExportJobStatus | string): Tone {
  switch (status) {
    case "SUCCEEDED":
      return "green";
    case "FAILED":
      return "red";
    case "RUNNING":
      return "blue";
    default:
      return "gold";
  }
}

export function exportJobStatusLabel(t: Translate, status: ExportJobStatus | string): string {
  switch (status) {
    case "QUEUED":
      return t("scale.export.status.QUEUED", "Waiting");
    case "RUNNING":
      return t("scale.export.status.RUNNING", "Preparing");
    case "SUCCEEDED":
      return t("scale.export.status.SUCCEEDED", "Ready");
    case "FAILED":
      return t("scale.export.status.FAILED", "Failed");
    default:
      return status;
  }
}

export function exportJobFilename(job: ExportJob): string {
  const named = job.parameters?.filename;
  if (typeof named === "string" && named) return named;
  return `${job.kind}-${job.id.slice(0, 8)}.${job.format.toLowerCase()}`;
}

export function jobAgeMinutes(job: ExportJob, now: number = Date.now()): number {
  const created = Date.parse(job.created_at);
  return Number.isFinite(created) ? Math.max(0, Math.floor((now - created) / 60000)) : 0;
}

export function downloadErrorKind(error: unknown): "not_ready" | "expired" | "other" {
  const code = getApiErrorCode(error);
  const status = httpStatus(error);
  if (code === "EXPORT_FILE_GONE" || status === 410) return "expired";
  if (code === "EXPORT_NOT_READY" || status === 409) return "not_ready";
  return "other";
}

export async function blobErrorMessage(error: unknown, fallback: string): Promise<string> {
  const data = (error as { response?: { data?: unknown } })?.response?.data;
  if (data instanceof Blob) {
    try {
      const body = JSON.parse(await data.text());
      return body?.error?.message ?? body?.detail ?? fallback;
    } catch {
      return fallback;
    }
  }
  return getApiErrorMessage(error, fallback);
}
import { ApiError } from "../../api/client";

export type Tx = (key: string, defaultValue: string, vars?: Record<string, unknown>) => string;

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

export function percentOf(value: number, limit: number | null | undefined): number {
  if (!limit || limit <= 0) return 0;
  return Math.max(0, Math.min(100, (value / limit) * 100));
}

export function budgetLabel(tx: Tx, name: string): string {
  if (name === "calculation_time") return tx("insight.budget.time", "Calculation time");
  if (name === "peak_memory") return tx("insight.budget.memory", "Peak memory");
  return name.replace(/_/g, " ");
}

export function fallbackReasonText(tx: Tx, reason: string | undefined): string | null {
  switch (reason) {
    case undefined:
    case "":
      return null;
    case "NO_BASELINE":
      return tx("insight.fallback.NO_BASELINE", "There was no earlier completed run to build on, so everything was calculated.");
    case "ALLOCATION_INPUTS_CHANGED":
      return tx("insight.fallback.ALLOCATION_INPUTS_CHANGED", "The rule set, convention or engine changed since the earlier run, so everything was calculated again.");
    case "TOO_MANY_CHANGES":
      return tx("insight.fallback.TOO_MANY_CHANGES", "Too much of the model changed for a partial update to be worthwhile, so everything was calculated again.");
    case "BASELINE_INCONSISTENT":
      return tx("insight.fallback.BASELINE_INCONSISTENT", "The earlier run's saved data no longer matched the model, so everything was calculated again.");
    case "VERIFY_MISMATCH":
      return tx("insight.fallback.VERIFY_MISMATCH", "The check found a difference between the partial update and a full calculation, so the full result was kept.");
    default:
      return reason.replace(/_/g, " ").toLowerCase();
  }
}

export type FailureInfo = { title: string; hint: string; retry: boolean };

export function runFailureInfo(tx: Tx, code: string | null | undefined): FailureInfo {
  switch (code) {
    case "RUN_STALE":
      return {
        title: tx("insight.failure.RUN_STALE.title", "The calculation stopped responding"),
        hint: tx("insight.failure.RUN_STALE.hint", "The worker running it went away before it finished. Start it again."),
        retry: true,
      };
    case "RUN_ENQUEUE_LOST":
    case "RUN_ENQUEUE_FAILED":
      return {
        title: tx("insight.failure.RUN_ENQUEUE_LOST.title", "The calculation never started"),
        hint: tx("insight.failure.RUN_ENQUEUE_LOST.hint", "The request was saved but could not be handed to a worker. Nothing was calculated. Start it again."),
        retry: true,
      };
    case "RUN_TIME_LIMIT":
      return {
        title: tx("insight.failure.RUN_TIME_LIMIT.title", "The calculation took too long"),
        hint: tx("insight.failure.RUN_TIME_LIMIT.hint", "It was stopped at the time limit. Try fewer drawing revisions at once, or ask support if this model is very large."),
        retry: false,
      };
    case "INPUT_CHANGED":
      return {
        title: tx("insight.failure.INPUT_CHANGED.title", "The drawings changed while it was running"),
        hint: tx("insight.failure.INPUT_CHANGED.hint", "A selected revision was edited or replaced mid-run, so the result would not match the drawings. Start it again."),
        retry: true,
      };
    case "SELF_CHECK_FAILED":
      return {
        title: tx("insight.failure.SELF_CHECK_FAILED.title", "The result failed its own checks"),
        hint: tx("insight.failure.SELF_CHECK_FAILED.hint", "The quantities did not add up, so nothing was published. Running again will not change that; report the run id to support."),
        retry: false,
      };
    case "RUN_FAILED":
      return {
        title: tx("insight.failure.RUN_FAILED.title", "The calculation failed"),
        hint: tx("insight.failure.RUN_FAILED.hint", "Something unexpected stopped it. You can start it again; if it keeps failing, report the run id to support."),
        retry: true,
      };
    default:
      return {
        title: tx("insight.failure.other.title", "The calculation did not finish"),
        hint: tx("insight.failure.other.hint", "See the message below."),
        retry: true,
      };
  }
}

export type StartErrorKind = "concurrency" | "rate" | "quota" | "in_progress" | "other";

export type StartRunError = {
  kind: StartErrorKind;
  code: string | null;
  message: string;
  retryable: boolean;
};

export function classifyStartError(err: unknown, fallback: string): StartRunError {
  const status = err instanceof ApiError ? err.status : undefined;
  const code = err instanceof ApiError ? err.code : null;
  const message = err instanceof Error && err.message ? err.message : fallback;
  if (code === "RUN_CONCURRENCY_LIMIT") return { kind: "concurrency", code, message, retryable: true };
  if (code === "RUN_RATE_LIMITED") return { kind: "rate", code, message, retryable: true };
  if (code === "RUN_IN_PROGRESS" || (status === 409 && !code)) return { kind: "in_progress", code, message, retryable: true };
  if (status === 402) return { kind: "quota", code, message, retryable: false };
  return { kind: "other", code, message, retryable: false };
}

export function startErrorGuidance(tx: Tx, kind: StartErrorKind): { title: string; hint: string } {
  switch (kind) {
    case "concurrency":
      return {
        title: tx("insight.start.concurrency.title", "Your company has enough calculations running already"),
        hint: tx("insight.start.concurrency.hint", "Wait for one of them to finish, then start this one. Nothing was lost."),
      };
    case "rate":
      return {
        title: tx("insight.start.rate.title", "Too many calculations started in a short time"),
        hint: tx("insight.start.rate.hint", "Give it a few minutes and try again. Calculation insights shows when the window resets."),
      };
    case "in_progress":
      return {
        title: tx("insight.start.inProgress.title", "This project is already being calculated"),
        hint: tx("insight.start.inProgress.hint", "A run for this project is still going. Wait for it to end, then try again."),
      };
    case "quota":
      return {
        title: tx("insight.start.quota.title", "Your plan has no calculation runs left"),
        hint: tx("insight.start.quota.hint", "The runs included in your plan for this period are used up. Review your subscription to add more."),
      };
    default:
      return { title: tx("insight.start.other.title", "The calculation could not be started"), hint: "" };
  }
}
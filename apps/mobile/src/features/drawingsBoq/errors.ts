import { ApiError } from "../../api/client";

const MESSAGES: Record<string, string> = {
  NO_PARSED_DRAWINGS:
    "No processed IFC drawing yet. Upload an IFC and wait until its status is PARSED.",
  RUN_IN_PROGRESS: "A calculation is already running for this project.",
  BOQ_IMMUTABLE: "This BOQ is locked in its current state and cannot be changed.",
  OPEN_BLOCKING_ISSUES: "Resolve or waive the blocking review issues first.",
  UNPRICED_ITEMS: "Price every item before moving on.",
  EXPORT_REQUIRES_APPROVED: "Approve the BOQ before exporting.",
  INVALID_LIFECYCLE_TRANSITION: "That action is not available in the current state.",
  WAIVER_REQUIRES_REASON: "Enter a reason to waive.",
  ADJUSTMENT_REQUIRES_REASON: "Enter a reason.",
  CONCURRENT_MODIFICATION: "This changed elsewhere. Refresh and try again.",
  USE_VERSION_APPROVAL: "Approve the whole version instead of single items.",
  UNIT_LOCKED: "The unit of a calculated item cannot be changed.",
  BBS_NO_SCHEDULED_STEEL: "No bar bending schedule data for this version.",
};

export function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.code && MESSAGES[err.code]) {
    return MESSAGES[err.code];
  }
  return err instanceof Error && err.message ? err.message : fallback;
}
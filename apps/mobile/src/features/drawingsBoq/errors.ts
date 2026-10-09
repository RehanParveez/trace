import { ApiError } from "../../api/client";

const MESSAGES: Record<string, string> = {
  NO_PARSED_DRAWINGS: "No processed IFC drawing yet. Upload an IFC and wait until its status is PARSED.",
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
  PENDING_ROWS_REMAIN: "Some rows are still pending. Confirm or reject them first.",
  NO_CONFIRMED_ROWS: "Confirm at least one row first.",
  IMPORT_NOT_EDITABLE: "This import can no longer be edited.",
  NOT_ENGINE_VERSION: "This is only available on calculated (engine) versions.",
  SPACE_NEEDS_NAME: "A room needs a number or a name.",
  SPACE_NOT_FOUND: "Room not found.",
  SPACE_NOT_IN_CURRENT_MODEL: "This room is not in the current model, so it cannot be previewed.",
  ELEMENT_NOT_FOUND: "Some of the chosen elements are not in the current model.",
  LEVEL_NOT_FOUND: "That level was not found.",
  RATE_BOOK_IMMUTABLE: "Only a draft rate book can be changed. Start a new version first.",
  RATE_BOOK_READ_ONLY: "This is a system rate book and cannot be changed.",
  RATE_BOOK_IN_USE: "BOQ lines use this rate book, so it cannot be deleted.",
  RATE_BOOK_EMPTY: "Add at least one active rate before publishing.",
  RATE_BOOK_IS_DRAFT: "This rate book is already a draft.",
  RATE_ITEM_EXISTS: "This work item already has a rate in that unit.",
  ESCALATION_EXISTS: "An escalation for this trade and date already exists.",
  RATE_OVERRIDE_EXISTS: "An override for this work item and unit already exists.",
  RATE_OVERRIDE_REVOKED: "This override is already revoked.",
  RATE_IMPORT_TOO_LARGE: "The CSV is too large (5 MB or 2000 rows at most).",
  INVALID_RATE_BOOK_STATE: "That action is not available for this rate book's status.",
  BAR_SIZE_EXISTS: "This bar size already exists.",
  RULESET_NOT_FOUND: "Rule set not found.",
  RULESET_SYSTEM_READONLY: "System rule sets are read-only. Clone it to get your own draft.",
  RULESET_IMMUTABLE: "A published rule set cannot be changed. Clone it to get a new draft.",
  CONVENTION_UNKNOWN: "That measurement convention is not available.",
  WORK_ITEM_ALREADY_EXISTS: "A work item with this code already exists.",
  WORK_ITEM_NOT_FOUND: "Work item not found.",
  WORK_ITEM_SYSTEM_READONLY: "System work items cannot be changed.",
};

export function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.code && MESSAGES[err.code]) {
    return MESSAGES[err.code];
  }
  return err instanceof Error && err.message ? err.message : fallback;
}
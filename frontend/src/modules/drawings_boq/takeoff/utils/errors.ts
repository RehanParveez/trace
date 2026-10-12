import { getApiErrorMessage } from "../../../identity";
import { getApiErrorCode } from "../../../../shared/utils/apiError";

export const TAKEOFF_ERROR_TEXT: Record<string, string> = {
  DRAWING_NOT_PDF: "This drawing is not a PDF, so it cannot be measured here.",
  PDF_UNREADABLE: "This PDF could not be read. Export it again from the CAD program and upload a new copy.",
  PDF_ENCRYPTED: "This PDF is password protected. Remove the password and upload it again.",
  PDF_EMPTY: "This PDF has no pages.",
  PDF_TOO_MANY_PAGES: "This PDF has more sheets than can be opened at once. Split it into smaller files.",
  SHEET_NOT_PREPARED: "This sheet has not been read yet. Prepare it first.",
  SHEET_PREP_FAILED: "This sheet could not be read. You can still draw on it by hand after calibrating.",
  SHEET_NOT_IN_DRAWING: "That sheet does not belong to this drawing.",
  SCALE_TEXT_UNREADABLE: "That scale could not be understood. Type it like 1:100 or 1/8\" = 1'-0\".",
  CALIBRATION_INCOMPLETE: "The calibration needs two points and the real distance between them.",
  CALIBRATION_UNUSABLE: "The calibration is not usable (for example its check dimension is off by more than 2%). Calibrate again.",
  CALIBRATION_IN_USE: "This calibration is used by measurements. Make another calibration the default before removing it.",
  CALIBRATION_WRONG_SHEET: "That calibration belongs to another sheet.",
  NO_SCALE_RECOMMENDATION: "No scale or readable dimensions were found on this sheet. Calibrate with two points and a known distance.",
  INVALID_MODE: "That way of measuring is not available for this kind of measurement.",
  INVALID_GEOMETRY: "The drawn shape is not valid. Check it has enough points.",
  SELF_INTERSECTING: "The outline crosses itself. Redraw it so the lines do not cross.",
  MEASUREMENT_NEEDS_WORK_ITEM: "Choose a work item before confirming.",
  WORK_ITEM_RESERVED: "Steel items are measured from the model and cannot be used for PDF takeoff.",
  WORK_ITEM_NOT_FOUND: "That work item does not exist.",
  PDF_UNCALIBRATED: "This sheet has no calibration yet. Calibrate it first.",
  ZERO_QUANTITY: "The quantity is zero, so there is nothing to confirm.",
  TAKEOFF_UNIT_MISMATCH: "The result of this measurement is in a different unit from the work item. Pick another mode or work item.",
  DUPLICATE_MEASUREMENT: "An identical confirmed measurement already exists for this work item. Confirming this one would count it twice.",
  TAG_NOT_FOUND: "That tag was not found on this sheet.",
  SHAPE_GROUP_NOT_FOUND: "That group of shapes was not found. Read the sheet again.",
  DRAWING_SELECTION_REQUIRED: "Choose the drawings to include in the run.",
  DRAWING_NOT_ELIGIBLE: "One of the chosen drawings cannot be calculated yet.",
  NO_PARSED_DRAWINGS: "There is nothing to calculate yet: no parsed model and no confirmed PDF measurements.",
};

export function takeoffErrorCode(error: unknown): string | null {
  return getApiErrorCode(error);
}

export function takeoffErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  const code = getApiErrorCode(error);
  if (code && TAKEOFF_ERROR_TEXT[code]) return TAKEOFF_ERROR_TEXT[code];
  return getApiErrorMessage(error, fallback);
}

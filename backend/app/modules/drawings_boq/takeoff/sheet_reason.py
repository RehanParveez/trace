from __future__ import annotations
import os
import re
import traceback

READ_SHEETS = "READ_SHEETS"
CONFIRM_SCALE = "CONFIRM_SCALE"
MEASURE_BY_HAND = "MEASURE_BY_HAND"
REPORT_PROBLEM = "REPORT_PROBLEM"
NONE = "NONE"

ACTION_HINT = {
  READ_SHEETS: "Press Read sheets to try again.",
  CONFIRM_SCALE: "Confirm the scale of this sheet on the Measure page; once confirmed, the whole sheet is read.",
  MEASURE_BY_HAND: "This sheet is not read automatically. Take it off on the Measure page.",
  REPORT_PROBLEM: "The program failed while reading this sheet. Press Read sheets once more; if the same line comes back, send it to support.",
  NONE: "",
}

PREPARE_FAILED = "PREPARE_FAILED"
PROGRAM_ERROR = "PROGRAM_ERROR"
NOT_PREPARED = "NOT_PREPARED"

_PROGRAM_ERROR = re.compile(r"could not be read: [A-Za-z_][\w.]*(Error|Exception)\b")

def failure_text(page_no: int, exc: BaseException) -> str:
  """What is stored when a sheet could not be prepared: the kind of failure, its message and the place in the program where it happened.
  The place is the last frame of the traceback, so the line that failed is on the screen and in the report, not only in a log."""
  frames = traceback.extract_tb(exc.__traceback__)
  where = f" [{os.path.basename(frames[-1].filename)} line {frames[-1].lineno}, in {frames[-1].name}]" if frames else ""
  detail = " ".join(str(exc).split())[:200]
  head = f"Page {page_no} could not be read: {type(exc).__name__}"
  return f"{head}: {detail}{where}" if detail else f"{head}{where}"

def _is_scale(code: str | None) -> bool:
  return bool(code) and str(code).startswith("SCALE_")

def sheet_reason(state: str, page_no: int, prep_status: str | None, prep_error: str | None, issue: dict | None) -> dict:
  """state is READ, SET_ASIDE, WAITING or NOT_PREPARED. Returns {code, message, action}.

  A sheet that could not be prepared reports the preparation error, never an older read note: the old note describes a read
  that no longer matches the sheet."""
  issue = issue or {}
  code, message = issue.get("code"), issue.get("message")
  if state == "READ":
    return {"code": None, "message": None, "action": NONE}
  if state == "SET_ASIDE":
    return {"code": code, "message": message, "action": NONE}
  if state == "NOT_PREPARED":
    if prep_status == "FAILED" or prep_error:
      if prep_error and _PROGRAM_ERROR.search(prep_error):
        return {"code": PROGRAM_ERROR, "message": prep_error, "action": REPORT_PROBLEM}
      return {"code": PREPARE_FAILED, "message": prep_error or f"Sheet {page_no} could not be read.", "action": READ_SHEETS}
    return {"code": NOT_PREPARED, "message": f"Sheet {page_no} has not been prepared yet. It is prepared when the sheets are read.", "action": READ_SHEETS}
  if _is_scale(code):
    return {"code": code, "message": message, "action": CONFIRM_SCALE}
  if code or message:
    return {"code": code, "message": message, "action": MEASURE_BY_HAND}
  return {"code": None, "message": f"Sheet {page_no} has not been read yet.", "action": READ_SHEETS}
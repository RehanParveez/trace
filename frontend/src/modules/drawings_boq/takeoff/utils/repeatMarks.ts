import type { CandidateFailure } from "../types/takeoff.types";

export const REPEAT_MARK_CODE = "MARK_ACCEPTED_ELSEWHERE";

export function isRepeatMark(f: Pick<CandidateFailure, "code">): boolean {
  return f.code === REPEAT_MARK_CODE;
}

export function repeatMarks(failed: readonly CandidateFailure[]): CandidateFailure[] {
  return failed.filter(isRepeatMark);
}

export function otherFailures(failed: readonly CandidateFailure[]): CandidateFailure[] {
  return failed.filter((f) => !isRepeatMark(f));
}

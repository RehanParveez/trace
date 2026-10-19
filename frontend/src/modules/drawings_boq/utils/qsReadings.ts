import type { QsAnswer, QsAnswerStatus, QsAnswers } from "../api/qsReadings.api";

export const QS_STATUS_ORDER: QsAnswerStatus[] = ["OPEN", "CONFIRM", "PLOT", "APPLIED"];

export const QS_STATUS_LABEL: Record<QsAnswerStatus, string> = {
  APPLIED: "Applied",
  CONFIRM: "Confirm with the QS",
  OPEN: "Not answered yet",
  PLOT: "Belongs to one plot",
};

export const QS_STATUS_TONE: Record<QsAnswerStatus, "green" | "red" | "blue" | "gold" | "slate"> = {
  APPLIED: "green",
  CONFIRM: "gold",
  OPEN: "red",
  PLOT: "blue",
};

export interface QsSectionGroup {
  key: string;
  title: string;
  answers: QsAnswer[];
}

export function qsSectionGroups(data: QsAnswers | null | undefined): QsSectionGroup[] {
  if (!data) return [];
  const rank = (a: QsAnswer) => QS_STATUS_ORDER.indexOf(a.status);
  return data.sections
    .map((s) => ({
      key: s.key,
      title: s.title,
      answers: data.answers.filter((a) => a.section === s.key).sort((a, b) => rank(a) - rank(b)),
    }))
    .filter((g) => g.answers.length > 0);
}

export function qsWaitingCount(data: QsAnswers | null | undefined): number {
  if (!data) return 0;
  return (data.counts.OPEN ?? 0) + (data.counts.CONFIRM ?? 0);
}

export function qsFlagText(value: number | undefined): string | null {
  if (value === undefined) return null;
  return value >= 0.5 ? "Yes" : "No";
}

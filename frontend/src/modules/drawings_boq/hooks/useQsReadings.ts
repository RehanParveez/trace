import { useQuery } from "@tanstack/react-query";
import { qsAnswersApi } from "../api/qsReadings.api";
import { drawingsBoqKeys } from "./useDrawingsBoq";

export type { QsAnswer, QsAnswers, QsAnswerStatus } from "../api/qsReadings.api";

export const qsAnswersKey = [...drawingsBoqKeys.all, "qs-answers"] as const;

export function useQsAnswers() {
  return useQuery({ queryKey: qsAnswersKey, queryFn: () => qsAnswersApi.get(), staleTime: 5 * 60 * 1000 });
}

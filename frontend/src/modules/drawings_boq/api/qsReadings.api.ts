import { apiClient } from "../../../shared/api/client";

export type QsAnswerStatus = "APPLIED" | "CONFIRM" | "OPEN" | "PLOT";

export interface QsAnswer {
  id: string;
  section: string;
  topic: string;
  question: string;
  answer: string;
  status: QsAnswerStatus;
  applied: string;
  confirm: string | null;
  params: string[];
  conventions: string[];
  workbook: string | null;
}

export interface QsAnswers {
  qs: string;
  answered_on: string;
  sections: Array<{ key: string; title: string }>;
  answers: QsAnswer[];
  params: Record<string, number>;
  conventions: Record<string, number>;
  counts: Partial<Record<QsAnswerStatus, number>>;
}

export const qsAnswersApi = {
  async get(): Promise<QsAnswers> {
    const response = await apiClient.get<QsAnswers>("/drawings-boq/qs-answers");
    return response.data;
  },
};

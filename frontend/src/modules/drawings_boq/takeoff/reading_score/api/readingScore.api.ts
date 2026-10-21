import { apiClient } from "../../../../../shared/api/client";
import type { DeriveLabelsResult, ImportLabelsBody, ImportLabelsResult, LabelsSummary, LabelTemplate, RunScoreBody, ScoreCompare, ScoreDetail, ScoreList } from "../types/readingScore.types";

const BASE = "/drawings-boq";

export const readingScoreApi = {
  async labels(drawingId: string): Promise<LabelsSummary> {
    return (await apiClient.get<LabelsSummary>(`${BASE}/drawings/${drawingId}/takeoff/reading-labels`)).data;
  },
  async template(): Promise<LabelTemplate> {
    return (await apiClient.get<LabelTemplate>(`${BASE}/takeoff/reading-labels/template`)).data;
  },
  async derive(drawingId: string): Promise<DeriveLabelsResult> {
    return (await apiClient.post<DeriveLabelsResult>(`${BASE}/drawings/${drawingId}/takeoff/reading-labels/derive`)).data;
  },
  async importLabels(drawingId: string, body: ImportLabelsBody): Promise<ImportLabelsResult> {
    return (await apiClient.post<ImportLabelsResult>(`${BASE}/drawings/${drawingId}/takeoff/reading-labels/import`, body)).data;
  },
  async scores(drawingId: string): Promise<ScoreList> {
    return (await apiClient.get<ScoreList>(`${BASE}/drawings/${drawingId}/takeoff/reading-scores`)).data;
  },
  async run(drawingId: string, body: RunScoreBody): Promise<ScoreDetail> {
    return (await apiClient.post<ScoreDetail>(`${BASE}/drawings/${drawingId}/takeoff/reading-scores`, body)).data;
  },
  async score(scoreId: string): Promise<ScoreDetail> {
    return (await apiClient.get<ScoreDetail>(`${BASE}/takeoff/reading-scores/${scoreId}`)).data;
  },
  async compare(drawingId: string, a: string, b: string): Promise<ScoreCompare> {
    return (await apiClient.get<ScoreCompare>(`${BASE}/drawings/${drawingId}/takeoff/reading-scores/compare`, { params: { a, b } })).data;
  },
};

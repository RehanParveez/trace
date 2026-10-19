import { apiClient } from "../../../../shared/api/client";
import type { CombineResult, ConflictsResult, LinksResult, ResolveConflictsBody, ResolveConflictsResult, SteelConventions, SteelRollup } from "../types/review.types";

const BASE = "/drawings-boq";

export const reviewApi = {
  async combineFloorSources(drawingId: string): Promise<CombineResult> {
    return (await apiClient.post<CombineResult>(`${BASE}/drawings/${drawingId}/takeoff/floor-sources/combine`, {})).data;
  },
  async conflicts(drawingId: string, policy: Record<string, string> = {}): Promise<ConflictsResult> {
    const params: Record<string, string> = {};
    if (policy.SLAB_THICKNESS) params.slab_policy = policy.SLAB_THICKNESS;
    if (policy.BEAM_SECTION) params.beam_policy = policy.BEAM_SECTION;
    if (policy.SOURCE_COUNT) params.count_policy = policy.SOURCE_COUNT
    return (await apiClient.get<ConflictsResult>(`${BASE}/drawings/${drawingId}/takeoff/conflicts`, { params })).data;
  },
  async resolveConflicts(drawingId: string, body: ResolveConflictsBody): Promise<ResolveConflictsResult> {
    return (await apiClient.post<ResolveConflictsResult>(`${BASE}/drawings/${drawingId}/takeoff/conflicts/resolve`, body)).data;
  },
  async links(drawingId: string): Promise<LinksResult> {
    return (await apiClient.get<LinksResult>(`${BASE}/drawings/${drawingId}/takeoff/links`)).data;
  },
  async steelRollup(drawingId: string, conventions: Partial<SteelConventions> = {}): Promise<SteelRollup> {
    const params: Record<string, number> = {};
    for (const [k, v] of Object.entries(conventions)) if (typeof v === "number" && Number.isFinite(v)) params[k] = v;
    return (await apiClient.get<SteelRollup>(`${BASE}/drawings/${drawingId}/takeoff/steel-rollup`, { params })).data;
  },
};

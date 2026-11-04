import { apiClient } from "../../../../../shared/api/client";
import type { SteelBoq } from "../types/steelBoq.types";

const B = "/drawings-boq";

export const steelBoqApi = {
  async preview(versionId: string, itemId?: string | null) {
    return (await apiClient.get<SteelBoq>(`${B}/boq-versions/${versionId}/audited-steel`, { params: { item_id: itemId ?? undefined } })).data;
  },

  async apply(versionId: string, itemId?: string | null) {
    return (await apiClient.post<SteelBoq>(`${B}/boq-versions/${versionId}/audited-steel`, { item_id: itemId ?? null })).data;
  },
};

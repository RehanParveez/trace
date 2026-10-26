import { apiClient } from "../../../../shared/api/client";
import type { CompanyConventions, ConventionsUpdate } from "../types/companyConventions.types";

const BASE = "/drawings-boq/company-conventions";

export const companyConventionsApi = {
  async get(): Promise<CompanyConventions> {
    return (await apiClient.get<CompanyConventions>(BASE)).data;
  },
  async save(body: ConventionsUpdate): Promise<CompanyConventions> {
    return (await apiClient.put<CompanyConventions>(BASE, body)).data;
  },
  async adoptQs(): Promise<CompanyConventions> {
    return (await apiClient.post<CompanyConventions>(`${BASE}/adopt-qs`)).data;
  },
};

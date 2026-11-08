import { apiClient } from "../../../shared/api/client";

export interface BillingProfileOption {
  id: string;
  label: string;
}

export interface BillingProfileSetting {
  billing_profile: string | null;
  effective: string;
  profiles: BillingProfileOption[];
}

export const billingProfileApi = {
  async get(): Promise<BillingProfileSetting> {
    return (await apiClient.get<BillingProfileSetting>("/organizations/me/billing-profile")).data;
  },
  async set(billingProfile: string | null): Promise<BillingProfileSetting> {
    return (await apiClient.patch<BillingProfileSetting>("/organizations/me/billing-profile", { billing_profile: billingProfile })).data;
  },
};

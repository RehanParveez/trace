export type PhotoTagSource = "MANUAL" | "AI";

export interface Channel {
  id: string;
  phone_number_id: string;
  business_account_id: string;
  display_phone_number: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ChannelConnectRequest {
  phone_number_id: string;
  business_account_id: string;
  access_token: string;
  display_phone_number?: string | null;
}

export interface PhotoTag {
  id: string;
  tag: string;
  confidence: number | null;
  source: PhotoTagSource;
}

export interface PhotoTagCreateRequest {
  tag: string;
}

export interface SitePhoto {
  id: string;
  project_id: string | null;
  storage_key: string;
  photo_url: string;
  sender_phone_number: string | null;
  caption_raw: string | null;
  caption_parsed: Record<string, unknown>;
  location_text: string | null;
  photo_date: string | null;
  is_ai_tagged: boolean;
  tags: PhotoTag[];
  created_at: string;
}

export interface SitePhotoUpdateRequest {
  location_text?: string | null;
  photo_date?: string | null;
}

export interface SitePhotoAssignProjectRequest {
  project_id: string;
}

export interface SitePhotoListParams {
  projectId?: string;
  photoDateFrom?: string;
  photoDateTo?: string;
  tag?: string;
  unassignedOnly?: boolean;
  skip?: number;
  limit?: number;
}
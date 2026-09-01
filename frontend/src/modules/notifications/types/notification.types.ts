export type NotificationType =
  | "DRAWING_PARSED" | "DRAWING_FAILED" | "BOQ_ITEM_APPROVED"
  | "SITE_PHOTO_NEEDS_PROJECT" | "PROGRESS_CLAIM_SUBMITTED"
  | "PROGRESS_CLAIM_APPROVED" | "PROGRESS_CLAIM_REJECTED"
  | "SUBSCRIPTION_USAGE_WARNING" | "MEMBER_JOINED"
  | "ORGANIZATION_INVITATION_RECEIVED";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  link_path: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}
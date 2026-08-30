export const WHATSAPP_PERMISSIONS = {
  WHATSAPP_CHANNEL_MANAGE: "whatsapp_channel:manage",
  SITE_PHOTO_READ: "site_photo:read",
  SITE_PHOTO_MANAGE: "site_photo:manage",
} as const;

export type WhatsAppPermission = (typeof WHATSAPP_PERMISSIONS)[keyof typeof WHATSAPP_PERMISSIONS];

export function hasWhatsAppPermission(permissions: string[] | undefined, permission: WhatsAppPermission): boolean {
  return permissions?.includes(permission) ?? false;
}
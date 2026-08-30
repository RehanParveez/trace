export function formatPhotoDate(value: string | null): string {
  if (!value) return "No date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No date";
  return new Intl.DateTimeFormat("en-PK", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function formatCapturedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatPhoneNumber(value: string | null): string {
  if (!value) return "Unknown sender";
  return value.startsWith("+") ? value : `+${value}`;
}

export function getCaptionField(caption: Record<string, unknown>, key: string): string | null {
  const value = caption[key];
  return typeof value === "string" && value.trim() ? value : null;
}
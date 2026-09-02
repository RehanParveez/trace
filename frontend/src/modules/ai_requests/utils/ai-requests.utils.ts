import type { AIRequestPurpose, AIResponseStatus } from "../types/ai-requests.types";

export function formatAIPurpose(purpose: AIRequestPurpose): string {
  switch (purpose) {
    case "MATERIAL_NORMALIZATION": return "Material normalization";
    case "CAPTION_PARSING": return "Caption parsing";
    case "PHOTO_TAGGING": return "Photo tagging";
    default: return purpose;
  }
}

export function getAIStatusTone(status: AIResponseStatus): "green" | "red" {
  return status === "SUCCEEDED" ? "green" : "red";
}

export function formatLatency(ms: number | null): string {
  if (ms === null) return "—";
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

export function formatAITimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-PK", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
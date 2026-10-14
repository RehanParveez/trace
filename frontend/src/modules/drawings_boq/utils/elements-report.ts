export function elementsPdfFilename(original: string | null | undefined, filtered: boolean): string {
  const stem = (original ?? "drawing").replace(/\.[^./\\]+$/, "");
  const safe = stem.replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 80) || "drawing";
  return `Elements-${safe}${filtered ? "-filtered" : ""}.pdf`;
}

export function isTooLargeError(error: unknown): boolean {
  const response = (error as { response?: { status?: number } } | null | undefined)?.response;
  return response?.status === 422;
}

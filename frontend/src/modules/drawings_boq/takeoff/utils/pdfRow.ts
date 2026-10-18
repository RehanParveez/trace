export interface PdfRowRef {
  sheetId: string | null;
  candidateId: string | null;
  measurementId: string | null;
  review: string | null;
}

export function pdfRowRef(properties: Record<string, unknown> | null | undefined): PdfRowRef | null {
  const raw = (properties ?? {})["_pdf"];
  if (!raw || typeof raw !== "object") return null;
  const p = raw as Record<string, unknown>;
  const text = (v: unknown) => (typeof v === "string" && v ? v : null);
  return { sheetId: text(p.sheet_id), candidateId: text(p.candidate_id), measurementId: text(p.measurement_id), review: text(p.review) };
}

export function measureUrl(projectId: string, drawingId: string, ref: PdfRowRef | null): string {
  const base = `/app/takeoff/${encodeURIComponent(projectId)}/${encodeURIComponent(drawingId)}`;
  if (!ref?.sheetId) return base;
  return `${base}?sheet=${encodeURIComponent(ref.sheetId)}${ref.measurementId ? `&m=${encodeURIComponent(ref.measurementId)}` : ""}`;
}

export function canHide(ref: PdfRowRef | null): boolean {
  return Boolean(ref?.candidateId) && ref?.review === "NEW";
}
import { authenticatedRequest, authenticatedResponse } from "./client";
import type { ExportFile } from "./boqEngine";
import type {BarMark, CursorPage, Deduction, LedgerRow, ProjectBoqCount, QuantitySolid,
} from "./types";

const BASE = "/drawings-boq";
const LIMIT = 100;

async function getPage<T>(path: string, query: URLSearchParams): Promise<CursorPage<T>> {
  query.set("limit", String(LIMIT));
  const response = await authenticatedResponse(`${path}?${query.toString()}`);
  const rows = (await response.json()) as T[];
  return { rows, next: response.headers.get("X-Next-Cursor") };
}

function params(entries: Record<string, string | undefined>): URLSearchParams {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(entries)) {
    if (value && value.trim()) query.set(key, value.trim());
  }
  return query;
}

export function listSolids(
  runId: string,
  filters: { after?: string; role?: string },
): Promise<CursorPage<QuantitySolid>> {
  return getPage<QuantitySolid>(
    `${BASE}/calculation-runs/${runId}/solids`,
    params({ after: filters.after, role: filters.role }),
  );
}

export function listRunLedger(
  runId: string,
  filters: { after?: string; workItemCode?: string },
): Promise<CursorPage<LedgerRow>> {
  return getPage<LedgerRow>(
    `${BASE}/calculation-runs/${runId}/ledger`,
    params({ after: filters.after, work_item_code: filters.workItemCode }),
  );
}

export function listVersionLedger(
  versionId: string,
  filters: { after?: string; workItemCode?: string },
): Promise<CursorPage<LedgerRow>> {
  return getPage<LedgerRow>(
    `${BASE}/boq-versions/${versionId}/ledger`,
    params({ after: filters.after, work_item_code: filters.workItemCode }),
  );
}

export function listDeductions(
  runId: string,
  filters: { after?: string; deductionType?: string },
): Promise<CursorPage<Deduction>> {
  return getPage<Deduction>(
    `${BASE}/calculation-runs/${runId}/deductions`,
    params({ after: filters.after, deduction_type: filters.deductionType }),
  );
}

export function listBarMarks(
  runId: string,
  filters: { after?: string; provenance?: string; role?: string },
): Promise<CursorPage<BarMark>> {
  return getPage<BarMark>(
    `${BASE}/calculation-runs/${runId}/bar-marks`,
    params({ after: filters.after, provenance: filters.provenance, role: filters.role }),
  );
}

export function getBoqItemCounts(): Promise<ProjectBoqCount[]> {
  return authenticatedRequest<ProjectBoqCount[]>(`${BASE}/boq-item-counts`);
}

export async function downloadDrawingFile(drawingId: string, fallbackName: string): Promise<ExportFile> {
  const response = await authenticatedResponse(`${BASE}/drawings/${drawingId}/file`);
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  const filename = (match?.[1] ?? fallbackName).replace(/[^\w.\- ]/g, "_");
  const mime = response.headers.get("Content-Type") ?? "application/octet-stream";

  return {
    bytes: new Uint8Array(await response.arrayBuffer()),
    filename,
    mime,
  };
}
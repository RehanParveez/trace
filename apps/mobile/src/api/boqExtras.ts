import { authenticatedRequest, authenticatedResponse } from "./client";
import type { ExportFile } from "./boqEngine";
import type { DiffResult, DrawingElement, SnapshotItem } from "./types";

const BASE = "/drawings-boq";

export function listSnapshotItems(snapshotId: string): Promise<SnapshotItem[]> {
  return authenticatedRequest<SnapshotItem[]>(
    `${BASE}/boq-snapshots/${snapshotId}/items`,
  );
}

export function getVersionDiff(
  versionA: string,
  versionB: string,
  includeUnchanged = false,
): Promise<DiffResult> {
  const q = new URLSearchParams({
    include_unchanged: String(includeUnchanged),
    include_elements: "false",
  });
  return authenticatedRequest<DiffResult>(
    `${BASE}/boq-versions/${versionA}/diff/${versionB}?${q.toString()}`,
  );
}

export function listItemSourceElements(itemId: string): Promise<DrawingElement[]> {
  return authenticatedRequest<DrawingElement[]>(
    `${BASE}/boq-items/${itemId}/source-elements`,
  );
}

export async function downloadLegacyExport(
  versionId: string,
  fmt: "pdf" | "xlsx",
): Promise<ExportFile> {
  const response = await authenticatedResponse(
    `${BASE}/boq-versions/${versionId}/export/${fmt}`,
  );
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  const filename = (match?.[1] ?? `boq.${fmt}`).replace(/[^\w.\- ]/g, "_");
  const mime =
    response.headers.get("Content-Type") ??
    (fmt === "pdf"
      ? "application/pdf"
      : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

  return {
    bytes: new Uint8Array(await response.arrayBuffer()),
    filename,
    mime,
  };
}
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {Button, EmptyState, ErrorState, Icon, LoadingState, Badge,
} from "../../organizations/components/OrganizationUi";
import { drawingsBoqApi } from "../api/drawings-boq.api";
import {useDrawingElementsPage, useDrawingLevels,
} from "../hooks";
import type {Drawing, DrawingElement, DrawingElementFilters, NormalizationStatus,
} from "../types/drawings-boq.types";
import {formatQuantity, elementMeasureMode, triggerBlobDownload,
} from "../utils/drawings-boq.utils";
import { elementsPdfFilename, isTooLargeError } from "../utils/elements-report";
import { useDecideCandidates, useReadPdfDrawing, useSyncPdfRegister } from "../takeoff/hooks/useTakeoff";
import { ApprovePdfDialog } from "../takeoff/components/ApprovePdfDialog";
import { canHide, measureUrl, pdfRowRef } from "../takeoff/utils/pdfRow";
import type { ReadStage } from "../takeoff/hooks/useTakeoff";
import type { RegisterSyncResult } from "../takeoff/types/takeoff.types";
import { isPdfFormat, measureBadge, needsPerson, pagesFor, waitingLines } from "../takeoff/utils/register";
import { EVIDENCE_LABEL, EVIDENCE_TONE, evidenceCheck, evidenceCounts, evidenceTitle, rangeText, rowEvidence } from "../takeoff/utils/evidence";
import { CoveragePanel } from "../takeoff/components/CoveragePanel";
import { memberZ, zText } from "../takeoff/utils/floors";

interface DrawingElementsDialogProps {
  drawing: Drawing;
  onClose: () => void;
}

type CopyColumn = {
  header: string;
  numeric?: boolean;
  value: (element: DrawingElement, levelNames: Map<string, string>) => unknown;
};

const COPY_COLUMNS: CopyColumn[] = [
  { header: "ifc_type", value: (e) => e.ifc_type },
  { header: "name", value: (e) => e.name },
  { header: "structural_role", value: (e) => e.structural_role },
  { header: "discipline", value: (e) => e.discipline },
  { header: "level", value: (e, levels) => e.level_name ?? (e.level_id ? levels.get(e.level_id) : null) },
  { header: "material", value: (e) => e.raw_material_text },
  { header: "quantity", numeric: true, value: (e) => e.quantity },
  { header: "unit", value: (e) => e.unit },
  { header: "normalization_status", value: (e) => e.normalization_status },
  { header: "measure_mode", value: (e) => e.measure_mode ?? elementMeasureMode(e) },
  { header: "measured_as", value: (e) => e.measured_as },
  { header: "length_mm", numeric: true, value: (e) => e.length_mm },
  { header: "width_mm", numeric: true, value: (e) => e.width_mm },
  { header: "height_mm", numeric: true, value: (e) => e.height_mm },
  { header: "thickness_mm", numeric: true, value: (e) => e.thickness_mm },
  { header: "area_mm2", numeric: true, value: (e) => e.area_mm2 },
  { header: "volume_mm3", numeric: true, value: (e) => e.volume_mm3 },
  {
    header: "normalization_issues",
    value: (e) => (e.normalization_issues ?? [])
      .map((issue) => {
        const item = issue as { code?: string; message?: string };
        return [item.code, item.message].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join(" | "),
  },
  { header: "quantity_source", value: (e) => e.quantity_source },
  { header: "classification_source", value: (e) => e.classification_source },
  { header: "classification_confidence", numeric: true, value: (e) => e.classification_confidence },
  { header: "predefined_type", value: (e) => e.predefined_type },
  { header: "type_mark", value: (e) => e.type_mark },
  { header: "type_name", value: (e) => e.type_name },
  { header: "level_sequence", numeric: true, value: (e) => e.level_sequence },
  { header: "elevation_base_mm", numeric: true, value: (e) => e.elevation_base_mm },
  { header: "elevation_top_mm", numeric: true, value: (e) => e.elevation_top_mm },
  { header: "height_range", value: (e) => zText(memberZ(e.properties)) },
  { header: "bbox_min_x_mm", numeric: true, value: (e) => e.bbox_min_x_mm },
  { header: "bbox_min_y_mm", numeric: true, value: (e) => e.bbox_min_y_mm },
  { header: "bbox_min_z_mm", numeric: true, value: (e) => e.bbox_min_z_mm },
  { header: "bbox_max_x_mm", numeric: true, value: (e) => e.bbox_max_x_mm },
  { header: "bbox_max_y_mm", numeric: true, value: (e) => e.bbox_max_y_mm },
  { header: "bbox_max_z_mm", numeric: true, value: (e) => e.bbox_max_z_mm },
  { header: "geometry_kind", value: (e) => e.geometry_kind },
  { header: "id", value: (e) => e.id },
  { header: "ifc_global_id", value: (e) => e.ifc_global_id },
  { header: "properties_json", value: (e) => (e.properties && Object.keys(e.properties).length > 0 ? JSON.stringify(e.properties) : "") },
  { header: "evidence", value: (e) => rowEvidence(e.properties)?.grade ?? "" },
  { header: "evidence_to_check", value: (e) => evidenceCheck(rowEvidence(e.properties)) },
  { header: "quantity_low", numeric: true, value: (e) => rangeFigure(e, "low") },
  { header: "quantity_high", numeric: true, value: (e) => rangeFigure(e, "high") },
];

function rangeFigure(e: { quantity: unknown; properties?: Record<string, unknown> | null }, side: "low" | "high"): number | "" {
  const r = rowEvidence(e.properties)?.range;
  const q = Number(e.quantity);
  if (!r || !r.bounded || !Number.isFinite(q)) return "";
  const pct = side === "low" ? r.low_pct : r.high_pct;
  return pct === null ? "" : Math.round(q * (1 + pct / 100) * 10000) / 10000;
}

const KIND_ORDER = ["IfcFooting", "IfcColumn", "IfcBeam", "IfcSlab", "IfcWall", "IfcSpace", "IfcDoor", "IfcWindow"];
const NATURAL = new Intl.Collator("en", { numeric: true, sensitivity: "base" });

function levelNameOf(e: DrawingElement, levelNames: Map<string, string>): string {
  return e.level_name ?? (e.level_id ? levelNames.get(e.level_id) : undefined) ?? "";
}

function kindRank(type: string | null | undefined): number {
  const i = KIND_ORDER.indexOf(type ?? "");
  return i === -1 ? KIND_ORDER.length : i;
}

function sortRegister(rows: DrawingElement[], levelNames: Map<string, string>): DrawingElement[] {
  return [...rows].sort((a, b) =>
    (Number(a.level_sequence ?? 1e9) - Number(b.level_sequence ?? 1e9))
    || NATURAL.compare(levelNameOf(a, levelNames), levelNameOf(b, levelNames))
    || (kindRank(a.ifc_type) - kindRank(b.ifc_type))
    || NATURAL.compare(a.ifc_type ?? "", b.ifc_type ?? "")
    || NATURAL.compare(a.name ?? "", b.name ?? "")
    || NATURAL.compare(a.id, b.id));
}

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = typeof value === "string" ? value : typeof value === "object" ? JSON.stringify(value) : String(value);
  return text.replace(/[\t\r\n]+/g, " ");
}

function tsvField(text: string): string {
  return text.includes("\"") ? `"${text.replace(/"/g, "\"\"")}"` : text;
}

function toTabSeparated(rows: DrawingElement[], levelNames: Map<string, string>): string {
  const lines = [["#", ...COPY_COLUMNS.map((column) => column.header)].join("\t")];
  rows.forEach((element, index) => {
    lines.push([String(index + 1), ...COPY_COLUMNS.map((column) => tsvField(cell(column.value(element, levelNames))))].join("\t"));
  });
  return lines.join("\n");
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function toHtmlTable(rows: DrawingElement[], levelNames: Map<string, string>): string {
  const border = "border:1px solid #9aa7b8;padding:2px 6px;white-space:nowrap;";
  const text = "mso-number-format:'\\@';";
  const head = ["#", ...COPY_COLUMNS.map((column) => column.header)]
    .map((h) => `<th style="${border}background:#1f3a5f;color:#ffffff;font-weight:bold;text-align:left;">${escapeHtml(h)}</th>`)
    .join("");
  const body = rows.map((element, index) => {
    const cells = COPY_COLUMNS.map((column) => {
      const style = column.numeric ? `${border}text-align:right;` : `${border}${text}text-align:left;`;
      return `<td style="${style}">${escapeHtml(cell(column.value(element, levelNames)))}</td>`;
    });
    return `<tr><td style="${border}text-align:right;">${index + 1}</td>${cells.join("")}</tr>`;
  });
  return `<table style="border-collapse:collapse;font-family:Calibri,Arial,sans-serif;font-size:11pt;"><thead><tr>${head}</tr></thead><tbody>${body.join("")}</tbody></table>`;
}

async function copyText(text: string): Promise<void> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch {
    
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.top = "0";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  document.body.removeChild(area);
  if (!ok) throw new Error("copy failed");
}

async function copyTable(rows: DrawingElement[], levelNames: Map<string, string>): Promise<void> {
  const tsv = toTabSeparated(rows, levelNames);
  try {
    if (typeof ClipboardItem !== "undefined" && navigator.clipboard?.write) {
      await navigator.clipboard.write([
        new ClipboardItem({
          "text/html": new Blob([toHtmlTable(rows, levelNames)], { type: "text/html" }),
          "text/plain": new Blob([tsv], { type: "text/plain" }),
        }),
      ]);
      return;
    }
  } catch {
    
  }
  await copyText(tsv);
}

type CopyState =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "done"; rows: number }
  | { kind: "error" };

type PdfState =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "done" }
  | { kind: "error"; tooLarge: boolean };

const PAGE_SIZE = 1000;
const MAX_PAGES = 200;

export function DrawingElementsDialog({
  drawing,
  onClose,
}: DrawingElementsDialogProps) {
  const { t } = useTranslation();
  const [structuralRole, setStructuralRole] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [levelId, setLevelId] = useState("");
  const [normalizationStatus, setNormalizationStatus] = useState<NormalizationStatus | "">("");
  const [after, setAfter] = useState<string | null>(null);
  const elementsQuery =
    useDrawingElementsPage(
      drawing.id,
      {
        limit: PAGE_SIZE,
        cursor: after,
        structural_role:
          structuralRole.trim() || null,
        discipline:
          discipline.trim() || null,
        level_id:
          levelId || null,
        normalization_status:
          normalizationStatus || null,
      },
    );


  const levelsQuery =
    useDrawingLevels(drawing.id);

  const [items, setItems] = useState<DrawingElement[]>([]);

  useEffect(() => {
    const page = elementsQuery.data?.items;
    if (!page) return;
    setItems((previous) => {
      if (after === null) return page;
      const seen = new Set(previous.map((element) => element.id));
      return [...previous, ...page.filter((element) => !seen.has(element.id))];
    });
  }, [elementsQuery.data, after]);

  const levelNames = useMemo(
    () => new Map((levelsQuery.data ?? []).map((level) => [level.id, level.name])),
    [levelsQuery.data],
  );
  
  const rowsShown = useMemo(() => sortRegister(items, levelNames), [items, levelNames]);
  const total = elementsQuery.data?.total ?? null;
  const hasFilter = Boolean(structuralRole.trim() || discipline.trim() || levelId || normalizationStatus);

  const isPdf = isPdfFormat(drawing.format);
  const navigate = useNavigate();
  const syncRegister = useSyncPdfRegister(drawing.id);
  const readSheets = useReadPdfDrawing(drawing.id);
  const [approving, setApproving] = useState(false);
  const approvingRef = useRef(false);
  approvingRef.current = approving;
  const decide = useDecideCandidates(drawing.id, undefined);

  const [stage, setStage] = useState<ReadStage | null>(null);
  const { mutate: syncNow } = syncRegister;
  useEffect(() => {
    if (isPdf) syncNow();
  }, [isPdf, syncNow]);
  
  const reg: RegisterSyncResult | null = readSheets.data?.register ?? syncRegister.data ?? null;
  const reading = readSheets.isPending;
  const lines = waitingLines(reg, readSheets.data?.issues);
  const readPages = pagesFor(lines, "READ_SHEETS");
  const scalePages = pagesFor(lines, "CONFIRM_SCALE");
  const handPages = pagesFor(lines, "MEASURE_BY_HAND");
  const reportPages = pagesFor(lines, "REPORT_PROBLEM");

  const [showTools, setShowTools] = useState(true);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !approvingRef.current) {
        event.preventDefault();
        onClose();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const [copy, setCopy] = useState<CopyState>({ kind: "idle" });
  const resetTimer = useRef<number | null>(null);
  useEffect(() => () => {
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
  }, []);
  const nextCursor = elementsQuery.data?.nextCursor ?? null;

  const copyAll = useCallback(async () => {
    setCopy({ kind: "working" });
    try {
      let rows: DrawingElement[] = items;
    
      if (nextCursor !== null || items.length === 0) {
        const filters: DrawingElementFilters = {
          limit: PAGE_SIZE,
          structural_role: structuralRole.trim() || null,
          discipline: discipline.trim() || null,
          level_id: levelId || null,
          normalization_status: normalizationStatus || null,
        };
        const all: DrawingElement[] = [];
        const seen = new Set<string>();
        let cursor: string | null = null;
        for (let n = 0; n < MAX_PAGES; n += 1) {
          const page = await drawingsBoqApi.listDrawingElements(drawing.id, { ...filters, cursor });
          for (const element of page.items) {
            if (!seen.has(element.id)) {
              seen.add(element.id);
              all.push(element);
            }
          }
          cursor = page.nextCursor;
          if (cursor === null) break;
        }
        rows = all;
      }
      await copyTable(sortRegister(rows, levelNames), levelNames);
      setCopy({ kind: "done", rows: rows.length });
    } catch {
      setCopy({ kind: "error" });
    }
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => setCopy({ kind: "idle" }), 5000);
  }, [items, nextCursor, structuralRole, discipline, levelId, normalizationStatus, drawing.id, levelNames]);

  const [pdf, setPdf] = useState<PdfState>({ kind: "idle" });
  const pdfTimer = useRef<number | null>(null);
  useEffect(() => () => {
    if (pdfTimer.current !== null) window.clearTimeout(pdfTimer.current);
  }, []);

  const downloadPdf = useCallback(async () => {
    setPdf({ kind: "working" });
    try {
      const blob = await drawingsBoqApi.exportDrawingElementsPdf(drawing.id, {
        structural_role: structuralRole.trim() || null,
        discipline: discipline.trim() || null,
        level_id: levelId || null,
        normalization_status: normalizationStatus || null,
      });
      triggerBlobDownload(blob, elementsPdfFilename(drawing.original_filename, hasFilter));
      setPdf({ kind: "done" });
    } catch (error) {
      setPdf({ kind: "error", tooLarge: isTooLargeError(error) });
    }
    if (pdfTimer.current !== null) window.clearTimeout(pdfTimer.current);
    pdfTimer.current = window.setTimeout(() => setPdf({ kind: "idle" }), 6000);
  }, [drawing.id, drawing.original_filename, structuralRole, discipline, levelId, normalizationStatus, hasFilter]);

  const pdfLabel =
    pdf.kind === "working" ? t("drawings.elements.downloadingPdf", "Preparing PDF\u2026")
    : pdf.kind === "done" ? t("drawings.elements.downloadedPdf", "PDF downloaded")
    : pdf.kind === "error" ? t("drawings.elements.downloadPdfFailed", "PDF failed. Try again")
    : hasFilter ? t("drawings.elements.downloadPdfFiltered", "Download PDF (filtered)")
    : t("drawings.elements.downloadPdf", "Download PDF");

  const copyLabel =
    copy.kind === "working" ? t("drawings.elements.copying", "Copying\u2026")
    : copy.kind === "done" ? t("drawings.elements.copied", { defaultValue: "Copied {{count}} rows", count: copy.rows })
    : copy.kind === "error" ? t("drawings.elements.copyFailed", "Copy failed. Try again")
    : hasFilter ? t("drawings.elements.copyAllFiltered", "Copy all (filtered)")
    : t("drawings.elements.copyAll", "Copy all");

  const headers = [
    { key: "no", label: "#" },
    { key: "ifcType", label: t("drawings.elements.ifcType") },
    { key: "name", label: t("drawings.elements.name") },
    { key: "role", label: t("drawings.elements.role") },
    { key: "discipline", label: t("drawings.elements.discipline") },
    { key: "level", label: t("drawings.elements.level") },
    { key: "material", label: t("drawings.elements.material") },
    { key: "quantity", label: t("drawings.elements.quantity") },
    { key: "normalization", label: t("drawings.elements.normalization") },
    { key: "measured", label: t("drawings.elements.measuredAs", "Measured as") },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-stretch justify-center bg-[var(--color-trace-navy)]/70 p-2 backdrop-blur-[2px] sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={drawing.original_filename}
        className="flex h-full w-full max-w-[1800px] flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] shadow-[0_24px_70px_rgba(8,13,24,0.35)]"
      >
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate font-[Archivo] text-[17px] font-bold text-[var(--color-text-primary)]">
              {drawing.original_filename}
            </h2>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              {total !== null
                ? t("drawings.elements.countOf", { defaultValue: "{{shown}} of {{total}} elements", shown: items.length, total })
                : t("drawings.elements.count", { defaultValue: "{{shown}} elements", shown: items.length })}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={copy.kind === "working" || elementsQuery.isLoading}
              onClick={() => void copyAll()}
              title={t(
                "drawings.elements.copyAllHint",
                "Copies every row and every column of this register as one table, in reading order, ready to paste into Excel or Google Sheets",
              )}
            >
              <Icon name={copy.kind === "done" ? "check" : "copy"} size={15} />
              {copyLabel}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={pdf.kind === "working" || elementsQuery.isLoading || reading || syncRegister.isPending}
              onClick={() => void downloadPdf()}
              title={t(
                "drawings.elements.downloadPdfHint",
                "Downloads this register as a PDF to share: every row in reading order, a row-count check against the database, the rows by floor, type and status, and the flags",
              )}
            >
              <Icon name={pdf.kind === "done" ? "check" : "download"} size={15} />
              {pdfLabel}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowTools((value) => !value)}
              aria-expanded={showTools}
            >
              <Icon name="filter" size={15} />
              {showTools
                ? t("drawings.elements.hideFilters", "Hide filters")
                : t("drawings.elements.showFilters", "Show filters")}
            </Button>
            <button
              ref={closeRef}
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] text-[var(--color-text-secondary)] outline-none transition hover:bg-[var(--color-surface)] focus-visible:ring-2 focus-visible:ring-[var(--color-trace-gold)]"
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        </div>

        {showTools ? (
          <div className="max-h-[34vh] shrink-0 space-y-3 overflow-y-auto border-b border-[var(--color-border)] px-4 py-3">
            <p className="text-[12px] text-[var(--color-text-muted)]">
              {isPdf ? t("drawings.elements.pdfDescription", "Items read from the sheets of this PDF. Each mark is one row. Review and measure them on the Measure page.") : t("drawings.elements.description")}
            </p>

            {isPdf ? (
              <div className="space-y-2 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[12px]">
                {reg ? (
                  <p className="font-semibold text-[var(--color-text-primary)]">
                    {t("drawings.elements.pdfSummary", {
                      defaultValue: "{{total}} items listed from {{read}} of {{sheets}} sheets. {{measured}} measured, {{review}} need a look.",
                      total: reg.total, read: reg.sheets_read, sheets: reg.sheets, measured: reg.measured, review: reg.needs_review,
                    })}
                  </p>
                ) : syncRegister.isPending ? (
                  <p>{t("drawings.elements.pdfListing", "Listing the items read from this PDF\u2026")}</p>
                ) : null}
                {reg && evidenceCounts(reg.evidence) ? (
                  <p className="text-[var(--color-text-secondary)]">
                    {t("drawings.elements.pdfEvidence", {
                      defaultValue: "{{printed}} printed, {{measured}} measured, {{assumed}} assumed, {{missing}} missing.",
                      ...evidenceCounts(reg.evidence),
                    })}
                    {reg.needs_review > 0 && (reg.decisions ?? 0) > 0 ? ` ${t("drawings.elements.pdfDecisions", {
                      defaultValue: "{{decisions}} decisions cover the {{review}} rows that need a look.",
                      decisions: reg.decisions, review: reg.needs_review,
                    })}` : ""}
                  </p>
                ) : null}
                {reg ? <CoveragePanel register={reg} /> : null}
                {reg && (reg.floors_to_decide ?? 0) > 0 ? (
                  <p className="text-[var(--color-warning)]" data-testid="floors-undecided">
                    {t("drawings.elements.pdfFloorsUndecided", {
                      defaultValue: "{{n}} floor(s) are open on two sheets ({{floors}}), so their quantities may be counted twice until you choose the sheet to use.",
                      n: reg.floors_to_decide,
                      floors: (reg.floors_undecided ?? []).map((f) => f.floor.toLowerCase()).join(", "),
                    })}
                  </p>
                ) : null}
                {needsPerson(reg) ? (
                  <div className="space-y-1">
                    {lines.map((line) => (
                      <p key={line.page_no} className="text-[var(--color-danger)]">
                        {t("drawings.elements.pdfIssue", {
                          defaultValue: "Sheet {{page}}: {{message}}",
                          page: line.page_no,
                          message: line.message || t("drawings.elements.pdfSheetUnread", "Not read yet."),
                        })}
                      </p>
                    ))}
                    {readPages ? (
                      <p className="text-[var(--color-text-muted)]">
                        {t("drawings.elements.pdfHintRead", { defaultValue: "Sheet {{pages}}: press Read sheets to try again.", pages: readPages })}
                      </p>
                    ) : null}
                    {scalePages ? (
                      <p className="text-[var(--color-text-muted)]">
                        {t("drawings.elements.pdfHintScale", {
                          defaultValue: "Sheet {{pages}}: open Measure and confirm the scale. Once confirmed, the whole sheet is read.",
                          pages: scalePages,
                        })}
                      </p>
                    ) : null}
                    {handPages ? (
                      <p className="text-[var(--color-text-muted)]">
                        {t("drawings.elements.pdfHintHand", {
                          defaultValue: "Sheet {{pages}} is not read automatically. Open Measure to take it off by hand.",
                          pages: handPages,
                        })}
                      </p>
                    ) : null}
                    {reportPages ? (
                      <p className="text-[var(--color-text-muted)]">
                        {t("drawings.elements.pdfHintReport", {
                          defaultValue: "Sheet {{pages}}: the program failed while reading this sheet. Press Read sheets once more. If the same line comes back, send it to support.",
                          pages: reportPages,
                        })}
                      </p>
                    ) : null}
                  </div>
                ) : null}
                {readSheets.isError || syncRegister.isError ? (
                  <p className="text-[var(--color-danger)]">
                    {t("drawings.elements.pdfFailed", "The sheets could not be read just now. Try again, or measure by hand on the Measure page.")}
                  </p>
                ) : null}
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={reading || syncRegister.isPending}
                    onClick={() => readSheets.mutate({ onStage: setStage })}
                  >
                    {reading
                      ? stage === "PREPARE" ? t("drawings.elements.pdfPreparing", "Preparing sheets\u2026")
                        : stage === "LIST" ? t("drawings.elements.pdfListingShort", "Listing items\u2026")
                        : t("drawings.elements.pdfReading", "Reading sheets\u2026")
                      : t("drawings.elements.pdfReadSheets", "Read sheets")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/app/takeoff/${drawing.project_id}/${drawing.id}`)}
                  >
                    {t("drawings.elements.pdfReview", "Review and measure")}
                  </Button>
                  <Button variant="primary" size="sm" onClick={() => setApproving(true)} disabled={reading || syncRegister.isPending}>
                    <Icon name="check" size={13} />
                    {t("takeoff.approve.tableButton", "Approve items")}
                  </Button>
                </div>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <input
                value={structuralRole}
                onChange={(event) => {
                  setStructuralRole(event.target.value);
                  setAfter(null);
                }}
                placeholder={t("drawings.elements.structuralRole")}
                aria-label={t("drawings.elements.structuralRole")}
                className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
              />

              <input
                value={discipline}
                onChange={(event) => {
                  setDiscipline(event.target.value);
                  setAfter(null);
                }}
                placeholder={t("drawings.elements.discipline")}
                aria-label={t("drawings.elements.discipline")}
                className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
              />

              <select
                value={levelId}
                onChange={(event) => {
                  setLevelId(event.target.value);
                  setAfter(null);
                }}
                aria-label={t("drawings.elements.level")}
                className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
              >
                <option value="">
                  {t("drawings.elements.allLevels")}
                </option>

                {(levelsQuery.data ?? []).map((level) => (
                  <option key={level.id} value={level.id}>
                    {level.name}
                  </option>
                ))}
              </select>

              <select
                value={normalizationStatus}
                onChange={(event) => {
                  setNormalizationStatus(event.target.value as NormalizationStatus | "");
                  setAfter(null);
                }}
                aria-label={t("drawings.elements.normalization")}
                className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px]"
              >
                <option value="">
                  {t("drawings.elements.allNormalizationStates")}
                </option>
                <option value="PENDING">{t("drawings.elements.pending")}</option>
                <option value="VALID">{t("drawings.elements.valid")}</option>
                <option value="WARNING">{t("drawings.elements.warning")}</option>
                <option value="INVALID">{t("drawings.elements.invalid")}</option>
              </select>
            </div>
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-auto bg-[var(--color-surface)]">
          {elementsQuery.isLoading && items.length === 0 ? (
            <LoadingState label={t("drawings.elements.loading")} />
          ) : elementsQuery.isError ? (
            <ErrorState
              title={t("drawings.elements.errorTitle")}
              onRetry={() => void elementsQuery.refetch()}
            />
          ) : items.length === 0 ? (
            <EmptyState
              icon="info"
              title={t("drawings.elements.emptyTitle")}
              description={isPdf && !hasFilter
                ? t("drawings.elements.pdfEmptyDescription", "Nothing was found on this PDF yet. Press Read sheets. A scanned sheet cannot be read automatically; measure it by hand.")
                : t("drawings.elements.emptyDescription")}
            />
          ) : (
            <table className="w-full min-w-[1100px] border-separate border-spacing-0 text-left">
              <thead>
                <tr>
                  {(isPdf ? [...headers, { key: "actions", label: t("drawings.elements.actions", "Actions") }] : headers).map((header) => (
                    <th
                      key={header.key}
                      className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]"
                    >
                      {header.label}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {rowsShown.map((element, index) => {
                  const badge = measureBadge(element.measure_mode ?? elementMeasureMode(element));
                  const evidence = rowEvidence(element.properties);
                  const heightRange = zText(memberZ(element.properties));
                  return (
                    <tr key={element.id} className="hover:bg-[var(--color-surface-muted)]">
                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 font-mono text-[10px] text-[var(--color-text-muted)]">
                        {index + 1}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 font-mono text-[11px]">
                        {element.ifc_type}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 text-[12px]">
                        {element.name ?? "\u2014"}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 text-[11px]">
                        {element.structural_role ?? "\u2014"}
                        {element.predefined_type && element.predefined_type !== element.structural_role
                          ? ` (${element.predefined_type})`
                          : ""}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 text-[11px]">
                        {element.discipline ?? "\u2014"}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 text-[11px]">
                        {element.level_name
                          ?? (element.level_id ? levelNames.get(element.level_id) : undefined)
                          ?? "\u2014"}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 text-[11px]">
                        {element.raw_material_text ?? "\u2014"}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 font-mono text-[11px]">
                        {formatQuantity(element.quantity)}{" "}
                        {element.unit ?? ""}
                      </td>

                      <td
                        className="border-b border-[var(--color-border)] px-3 py-2.5 text-[10px]"
                        title={(element.normalization_issues ?? [])
                          .map((issue) => (issue as { message?: string }).message)
                          .filter(Boolean)
                          .join("\n") || undefined}
                      >
                        {element.normalization_status ?? "\u2014"}
                        {evidence ? (
                          <div className="mt-1" title={evidenceTitle(evidence, Number(element.quantity), element.unit)}>
                            <Badge tone={EVIDENCE_TONE[evidence.grade]}>
                              {t(`drawings.elements.evidence.${evidence.grade}`, EVIDENCE_LABEL[evidence.grade])}
                            </Badge>
                            {evidence.range ? (
                              <div className="mt-0.5 font-mono text-[10px] text-[var(--color-text-muted)]" data-testid="row-range">
                                {rangeText(evidence.range, Number(element.quantity), element.unit)}
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </td>

                      <td className="border-b border-[var(--color-border)] px-3 py-2.5 text-[10px]">
                        <div title={element.measured_as ?? undefined}>
                          {badge === null ? "\u2014" : (
                            <Badge tone={badge.tone}>
                              {badge.label}
                            </Badge>
                          )}
                          {element.measured_as ? (
                            <div className="mt-1 text-[10px] text-[var(--color-text-muted)]">
                              {element.measured_as}
                            </div>
                          ) : null}
                          {heightRange ? (
                            <div className="mt-1 text-[10px] text-[var(--color-text-muted)]" data-testid="element-height-range">
                              {t("drawings.elements.heightRange", "Height {{range}}", { range: heightRange })}
                            </div>
                          ) : null}
                        </div>
                      </td>

                      {isPdf ? (
                        <td className="whitespace-nowrap border-b border-[var(--color-border)] px-3 py-2.5 text-[11px]">
                          <Button variant="ghost" size="sm" onClick={() => navigate(measureUrl(drawing.project_id, drawing.id, pdfRowRef(element.properties)))}>
                            {t("drawings.elements.open", "Open")}
                          </Button>
                          {canHide(pdfRowRef(element.properties)) ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={decide.isPending}
                              title={t("drawings.elements.hideHint", "Set this item aside. It leaves this list and the calculation. Bring it back on the Measure page.")}
                              onClick={() => {
                                const ref = pdfRowRef(element.properties);
                                if (!ref?.candidateId) return;
                                decide.mutate({ ids: [ref.candidateId], action: "reject" }, {
                                  onSuccess: () => {
                                    setItems((previous) => previous.filter((e) => e.id !== element.id));
                                    void elementsQuery.refetch();
                                  },
                                });
                              }}
                            >
                              {t("drawings.elements.hide", "Hide")}
                            </Button>
                          ) : null}
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border)] px-4 py-2.5">
          <p className="text-[11px] text-[var(--color-text-muted)]">
            {items.length > 0
              ? total !== null
                ? `Showing ${items.length} of ${total} elements`
                : `Showing ${items.length} elements`
              : ""}
            {copy.kind === "done" ? ` \u00b7 ${t("drawings.elements.copiedHint", "Copied. Paste it into Excel or Google Sheets.")}` : ""}
            {copy.kind === "error" ? ` \u00b7 ${t("drawings.elements.copyFailedHint", "The browser did not allow copying.")}` : ""}
            {pdf.kind === "done" ? ` \u00b7 ${t("drawings.elements.downloadedPdfHint", "The PDF is downloaded. Its first page states the row count and the check against the database.")}` : ""}
            {pdf.kind === "error" ? ` \u00b7 ${pdf.tooLarge
              ? t("drawings.elements.downloadPdfTooLarge", "This view has too many rows for one PDF. Filter by floor or type and download each part.")
              : t("drawings.elements.downloadPdfFailedHint", "The PDF could not be made just now. Try again.")}` : ""}
          </p>

          {nextCursor ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={elementsQuery.isFetching}
              onClick={() => setAfter(nextCursor)}
            >
              {t("drawings.elements.loadMore")}
            </Button>
          ) : null}
        </div>
      </div>
      {approving ? (
        <ApprovePdfDialog projectId={drawing.project_id} drawingId={drawing.id} filename={drawing.original_filename} onClose={() => setApproving(false)} />
      ) : null}
    </div>
  );
}

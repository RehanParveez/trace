import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PDFPageProxy } from "pdfjs-dist";
import { PdfSheetViewer } from "../../components/PdfSheetViewer";
import type { PointerInfo, ViewerHandle } from "../../components/PdfSheetViewer";
import type { PdfLoadState } from "../../hooks/usePdfDocument";
import { toScreen } from "../../utils/viewport";
import type { Matrix } from "../../utils/viewport";
import type { Box, ManualMark, ReportItem } from "../types/readingReport.types";
import { boxTooSmall, itemAt, normaliseBox, STATUS_COLOUR, STATUS_TEXT } from "../utils/readingReport";

interface Props {
  pdf: PdfLoadState;
  pageNo: number;
  items: ReportItem[];
  marks?: ManualMark[];
  selectedId: string | null;
  onSelect: (item: ReportItem | null) => void;
  cropMode?: boolean;
  onCrop?: (box: Box) => void;
  focusBox?: Box | null;
}

const FILL_ALPHA = "33";

function paintItem(ctx: CanvasRenderingContext2D, m: Matrix, it: ReportItem, selected: boolean) {
  const colour = STATUS_COLOUR[it.status] ?? "#475467";
  const pts = it.points.map((p) => toScreen(m, p));
  if (!pts.length) return;
  ctx.strokeStyle = colour;
  ctx.fillStyle = colour;
  ctx.lineWidth = selected ? 3.5 : 2;
  if (it.status === "UNSURE") ctx.setLineDash([6, 3]);
  else ctx.setLineDash([]);
  if (pts.length === 1 || it.kind === "COUNT") {
    for (const p of pts) {
      ctx.beginPath();
      ctx.arc(p[0], p[1], selected ? 7 : 5, 0, Math.PI * 2);
      ctx.fillStyle = colour + (selected ? "AA" : FILL_ALPHA);
      ctx.fill();
      ctx.stroke();
    }
  } else {
    ctx.beginPath();
    pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p[0], p[1]) : ctx.lineTo(p[0], p[1])));
    if (it.kind === "AREA") {
      ctx.closePath();
      ctx.fillStyle = colour + FILL_ALPHA;
      ctx.fill();
    }
    ctx.stroke();
  }
  ctx.setLineDash([]);
}

function paintMark(ctx: CanvasRenderingContext2D, m: Matrix, mk: ManualMark) {
  ctx.strokeStyle = "#175cd3";
  ctx.lineWidth = 2;
  ctx.setLineDash([2, 3]);
  const b = mk.geometry.box;
  if (b && b.length === 4) {
    const a = toScreen(m, [b[0] as number, b[1] as number]);
    const c = toScreen(m, [b[2] as number, b[3] as number]);
    ctx.strokeRect(Math.min(a[0], c[0]), Math.min(a[1], c[1]), Math.abs(c[0] - a[0]), Math.abs(c[1] - a[1]));
  } else {
    for (const p of mk.geometry.points ?? []) {
      const s = toScreen(m, p);
      ctx.strokeRect(s[0] - 6, s[1] - 6, 12, 12);
    }
  }
  ctx.setLineDash([]);
}

export function SheetViewer({ pdf, pageNo, items, marks = [], selectedId, onSelect, cropMode = false, onCrop, focusBox = null }: Props) {
  const handle = useRef<ViewerHandle>(null);
  const [page, setPage] = useState<PDFPageProxy | null>(null);
  const [cropA, setCropA] = useState<[number, number] | null>(null);
  const [hover, setHover] = useState<[number, number] | null>(null);

  useEffect(() => {
    setPage(null);
    if (pdf.status !== "ready") return;
    let cancelled = false;
    pdf.doc
      .getPage(Math.min(Math.max(pageNo, 1), pdf.doc.numPages))
      .then((p) => {
        if (!cancelled) setPage(p);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [pdf, pageNo]);

  useEffect(() => {
    if (!cropMode) setCropA(null);
  }, [cropMode]);

  useEffect(() => {
    if (focusBox) handle.current?.focusBox({ x0: focusBox[0], y0: focusBox[1], x1: focusBox[2], y1: focusBox[3] });
  }, [focusBox]);

  const paint = useCallback(
    (ctx: CanvasRenderingContext2D, m: Matrix) => {
      for (const it of items) if (it.id !== selectedId) paintItem(ctx, m, it, false);
      const sel = items.find((i) => i.id === selectedId);
      if (sel) paintItem(ctx, m, sel, true);
      for (const mk of marks) paintMark(ctx, m, mk);
      if (cropMode && cropA && hover) {
        const a = toScreen(m, cropA);
        const b = toScreen(m, hover);
        ctx.strokeStyle = "#c4320a";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 3]);
        ctx.strokeRect(Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]));
        ctx.setLineDash([]);
      }
    },
    [items, marks, selectedId, cropMode, cropA, hover],
  );

  const onPick = useCallback(
    (info: PointerInfo) => {
      if (cropMode) {
        if (!cropA) {
          setCropA([info.pt[0], info.pt[1]]);
          return;
        }
        const box = normaliseBox(cropA, [info.pt[0], info.pt[1]]);
        setCropA(null);
        setHover(null);
        if (!boxTooSmall(box)) onCrop?.(box);
        return;
      }
      onSelect(itemAt(items, info.pt[0], info.pt[1], Math.max(info.radiusPt, 3)));
    },
    [cropMode, cropA, items, onCrop, onSelect],
  );

  const onHover = useCallback((info: PointerInfo | null) => setHover(info && cropMode ? [info.pt[0], info.pt[1]] : null), [cropMode]);
  const paintKey = useMemo(() => ({ items, marks, selectedId, cropA, hover, cropMode }), [items, marks, selectedId, cropA, hover, cropMode]);

  if (pdf.status === "loading") return <div className="flex h-full items-center justify-center text-[12.5px] text-[var(--color-text-muted)]">Loading the drawing… {Math.round(pdf.progress * 100)} %</div>;
  if (pdf.status === "error") return <div className="flex h-full items-center justify-center text-[12.5px] text-[var(--color-danger)]">The drawing could not be opened.</div>;

  return (
    <div className="relative h-full min-h-[420px] overflow-hidden rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)]" data-testid="report-sheet-viewer">
      <PdfSheetViewer
        ref={handle}
        page={page}
        snapIndex={null}
        snapActive={false}
        snapKinds={[]}
        cursor={cropMode ? "crosshair" : "default"}
        panTool={false}
        paint={paint}
        paintKey={paintKey}
        onHover={onHover}
        onPick={onPick}
        onDoubleClick={() => undefined}
      />
      <div className="absolute left-2 top-2 flex gap-1" role="group" aria-label="Zoom">
        <button type="button" className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[12px]" onClick={() => handle.current?.zoomBy(1.4)} aria-label="Zoom in">+</button>
        <button type="button" className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[12px]" onClick={() => handle.current?.zoomBy(1 / 1.4)} aria-label="Zoom out">−</button>
        <button type="button" className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[12px]" onClick={() => handle.current?.fit()}>Fit</button>
      </div>
      {cropMode ? (
        <p className="absolute bottom-2 left-2 rounded-[6px] bg-[var(--color-surface)] px-2 py-1 text-[11.5px] shadow" data-testid="crop-hint">
          {cropA ? "Click the opposite corner." : "Click one corner of the area."}
        </p>
      ) : (
        <ul className="absolute bottom-2 left-2 flex gap-2 rounded-[6px] bg-[var(--color-surface)] px-2 py-1 text-[11px] shadow" aria-label="Colours">
          {Object.entries(STATUS_TEXT).filter(([k]) => k !== "NOT_RUN" && k !== "NOTHING_EXPECTED").map(([k, v]) => (
            <li key={k} className="flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: STATUS_COLOUR[k] }} />{v}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

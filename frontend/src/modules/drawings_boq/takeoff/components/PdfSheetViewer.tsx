import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from "react";
import type { PDFPageProxy } from "pdfjs-dist";
import type { Pt, SnapKind } from "../types/takeoff.types";
import type { SnapHit, SnapIndex } from "../utils/snapIndex";
import { fitView, pxToPt, toPdf, viewForBox, viewMatrix, zoomAt } from "../utils/viewport";
import type { Matrix, ViewState } from "../utils/viewport";

const MAX_CANVAS_PIXELS = 16_000_000;
const MAX_SERVER_SNAP_RADIUS_PT = 25;

export interface PointerInfo {
  pt: Pt;
  snap: SnapHit | null;
  sx: number;
  sy: number;
  radiusPt: number;
}

export interface ViewerHandle {
  fit: () => void;
  zoomBy: (factor: number) => void;
  focusBox: (box: { x0: number; y0: number; x1: number; y1: number }) => void;
  getView: () => ViewState;
  getMatrix: () => Matrix;
  pointerInfoAt: (sx: number, sy: number) => PointerInfo;
  repaint: () => void;
}

interface Props {
  page: PDFPageProxy | null;
  snapIndex: SnapIndex | null;
  snapActive: boolean;
  snapKinds: SnapKind[];
  snapRadiusPx?: number;
  cursor: string;
  panTool: boolean;
  
  paint: (ctx: CanvasRenderingContext2D, m: Matrix, size: { w: number; h: number }, view: ViewState) => void;
  paintKey: unknown;
  onHover: (info: PointerInfo | null) => void;
  onPick: (info: PointerInfo, event: PointerEvent) => void;
  onDoubleClick: (info: PointerInfo) => void;
  onViewChange?: (view: ViewState) => void;
  onRenderState?: (state: "idle" | "rendering" | "error") => void;
}

export const PdfSheetViewer = forwardRef<ViewerHandle, Props>(function PdfSheetViewer(props, ref) {
  const { page, snapIndex, snapActive, snapKinds, snapRadiusPx = 12, cursor, panTool, paint, paintKey, onHover, onPick, onDoubleClick, onViewChange, onRenderState } = props;

  const hostRef = useRef<HTMLDivElement>(null);
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);

  const viewRef = useRef<ViewState>({ zoom: 1, panX: 0, panY: 0 });
  const baseRef = useRef<Matrix>([1, 0, 0, 1, 0, 0]);
  const pageSizeRef = useRef({ w: 1, h: 1 });
  const sizeRef = useRef({ w: 0, h: 0 });
  const renderedRef = useRef<ViewState | null>(null);
  const taskRef = useRef<{ cancel: () => void } | null>(null);
  const renderTimer = useRef<number | null>(null);
  const drawRaf = useRef<number | null>(null);
  const spaceRef = useRef(false);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const dragRef = useRef<{ kind: "pan" | "click"; x: number; y: number; px: number; py: number; moved: boolean } | null>(null);
  const pinchRef = useRef<{ dist: number; cx: number; cy: number } | null>(null);
  const moveRaf = useRef<number | null>(null);
  const lastMove = useRef<{ x: number; y: number } | null>(null);

  const latest = useRef({ paint, snapIndex, snapActive, snapKinds, snapRadiusPx, panTool, onHover, onPick, onDoubleClick, onViewChange, onRenderState });
  latest.current = { paint, snapIndex, snapActive, snapKinds, snapRadiusPx, panTool, onHover, onPick, onDoubleClick, onViewChange, onRenderState };

  const dprFor = useCallback((w: number, h: number) => {
    const wanted = Math.min(window.devicePixelRatio || 1, 3);
    const cap = Math.sqrt(MAX_CANVAS_PIXELS / Math.max(w * h, 1));
    return Math.max(0.5, Math.min(wanted, cap));
  }, []);

  const applyCssTransform = useCallback(() => {
    const canvas = pdfCanvasRef.current;
    const rendered = renderedRef.current;
    if (!canvas || !rendered) return;
    const cur = viewRef.current;
    const k = cur.zoom / rendered.zoom;
    canvas.style.transform = `translate(${cur.panX - rendered.panX * k}px, ${cur.panY - rendered.panY * k}px) scale(${k})`;
  }, []);

  const drawOverlay = useCallback(() => {
    drawRaf.current = null;
    const canvas = overlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { w, h } = sizeRef.current;
    const dpr = canvas.width / Math.max(w, 1);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    latest.current.paint(ctx, viewMatrix(baseRef.current, viewRef.current), { w, h }, viewRef.current);
  }, []);

  const requestDraw = useCallback(() => {
    if (drawRaf.current === null) drawRaf.current = requestAnimationFrame(drawOverlay);
  }, [drawOverlay]);

  const doRender = useCallback(async () => {
    renderTimer.current = null;
    if (!page) return;
    const { w, h } = sizeRef.current;
    if (w < 2 || h < 2) return;
    taskRef.current?.cancel();
    const view = { ...viewRef.current };
    const dpr = dprFor(w, h);
    const off = document.createElement("canvas");
    off.width = Math.max(1, Math.ceil(w * dpr));
    off.height = Math.max(1, Math.ceil(h * dpr));
    const viewport = page.getViewport({ scale: view.zoom * dpr, offsetX: view.panX * dpr, offsetY: view.panY * dpr });
    const ctx = off.getContext("2d");
    if (!ctx) return;
    latest.current.onRenderState?.("rendering");
    const task = page.render({ canvas: off, canvasContext: ctx, viewport });
    taskRef.current = task;
    try {
      await task.promise;
    } catch (error) {
      if ((error as { name?: string })?.name !== "RenderingCancelledException") latest.current.onRenderState?.("error");
      return;
    }
    if (taskRef.current !== task) return;
    const target = pdfCanvasRef.current;
    if (!target) return;
    target.width = off.width;
    target.height = off.height;
    target.style.width = `${w}px`;
    target.style.height = `${h}px`;
    target.getContext("2d")?.drawImage(off, 0, 0);
    renderedRef.current = view;
    applyCssTransform();
    latest.current.onRenderState?.("idle");
  }, [page, dprFor, applyCssTransform]);

  const scheduleRender = useCallback(
    (delay = 110) => {
      if (renderTimer.current !== null) window.clearTimeout(renderTimer.current);
      renderTimer.current = window.setTimeout(() => void doRender(), delay);
    },
    [doRender],
  );

  const setView = useCallback(
    (next: ViewState, renderDelay = 110) => {
      viewRef.current = next;
      applyCssTransform();
      requestDraw();
      scheduleRender(renderDelay);
      latest.current.onViewChange?.(next);
    },
    [applyCssTransform, requestDraw, scheduleRender],
  );

  const fit = useCallback(() => {
    const { w, h } = sizeRef.current;
    setView(fitView(w, h, pageSizeRef.current.w, pageSizeRef.current.h), 0);
  }, [setView]);

  const infoAt = useCallback((sx: number, sy: number): PointerInfo => {
    const m = viewMatrix(baseRef.current, viewRef.current);
    const pt = toPdf(m, sx, sy);
    const radiusPt = Math.min(MAX_SERVER_SNAP_RADIUS_PT, Math.max(0.0001, pxToPt(latest.current.snapRadiusPx, viewRef.current.zoom)));
    const L = latest.current;
    const snap = L.snapActive && L.snapIndex ? L.snapIndex.nearest(pt[0], pt[1], radiusPt, L.snapKinds) : null;
    return { pt, snap, sx, sy, radiusPt };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      fit,
      zoomBy: (factor) => {
        const { w, h } = sizeRef.current;
        setView(zoomAt(viewRef.current, w / 2, h / 2, factor));
      },
      focusBox: (box) => {
        const { w, h } = sizeRef.current;
        setView(viewForBox(baseRef.current, box, w, h), 0);
      },
      getView: () => viewRef.current,
      getMatrix: () => viewMatrix(baseRef.current, viewRef.current),
      pointerInfoAt: infoAt,
      repaint: requestDraw,
    }),
    [fit, setView, infoAt, requestDraw],
  );

  useEffect(() => {
    if (!page) return;
    const vp = page.getViewport({ scale: 1 });
    baseRef.current = vp.transform as Matrix;
    pageSizeRef.current = { w: vp.width, h: vp.height };
    renderedRef.current = null;
    const { w, h } = sizeRef.current;
    if (w > 1) setView(fitView(w, h, vp.width, vp.height), 0);
    return () => {
      taskRef.current?.cancel();
      if (renderTimer.current !== null) window.clearTimeout(renderTimer.current);
    };
  }, [page, setView]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const apply = () => {
      const w = Math.max(1, Math.floor(host.clientWidth));
      const h = Math.max(1, Math.floor(host.clientHeight));
      const first = sizeRef.current.w === 0;
      sizeRef.current = { w, h };
      const overlay = overlayRef.current;
      if (overlay) {
        const dpr = dprFor(w, h);
        overlay.width = Math.ceil(w * dpr);
        overlay.height = Math.ceil(h * dpr);
        overlay.style.width = `${w}px`;
        overlay.style.height = `${h}px`;
      }
      if (first && page) {
        setView(fitView(w, h, pageSizeRef.current.w, pageSizeRef.current.h), 0);
      } else {
        requestDraw();
        scheduleRender(60);
      }
    };
    apply();
    const ro = new ResizeObserver(apply);
    ro.observe(host);
    return () => ro.disconnect();
  }, [page, dprFor, requestDraw, scheduleRender, setView]);

  useEffect(() => {
    requestDraw();
  }, [paintKey, requestDraw]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === "Space" && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement)) {
        spaceRef.current = true;
        e.preventDefault();
      }
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === "Space") spaceRef.current = false;
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, []);

  useEffect(() => {
    const el = overlayRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
      const factor = Math.exp(-e.deltaY * unit * 0.0016);
      setView(zoomAt(viewRef.current, e.clientX - rect.left, e.clientY - rect.top, factor));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [setView]);

  const local = (e: { clientX: number; clientY: number }) => {
    const rect = overlayRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const p = local(e);
    overlayRef.current?.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, p);
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      pinchRef.current = { dist: Math.hypot(a.x - b.x, a.y - b.y), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
      dragRef.current = null;
      return;
    }
    const wantsPan = e.button === 1 || e.button === 2 || spaceRef.current || latest.current.panTool;
    dragRef.current = { kind: wantsPan ? "pan" : "click", x: p.x, y: p.y, px: viewRef.current.panX, py: viewRef.current.panY, moved: false };
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const p = local(e);
    if (pointers.current.has(e.pointerId)) pointers.current.set(e.pointerId, p);
    if (pointers.current.size === 2 && pinchRef.current) {
      const [a, b] = [...pointers.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const cx = (a.x + b.x) / 2;
      const cy = (a.y + b.y) / 2;
      let v = zoomAt(viewRef.current, cx, cy, dist / Math.max(pinchRef.current.dist, 1));
      v = { ...v, panX: v.panX + (cx - pinchRef.current.cx), panY: v.panY + (cy - pinchRef.current.cy) };
      pinchRef.current = { dist, cx, cy };
      setView(v);
      return;
    }
    const drag = dragRef.current;
    if (drag) {
      const dx = p.x - drag.x;
      const dy = p.y - drag.y;
      if (Math.hypot(dx, dy) > 4) drag.moved = true;
      if (drag.kind === "pan" && drag.moved) {
        setView({ ...viewRef.current, panX: drag.px + dx, panY: drag.py + dy });
        return;
      }
    }
    lastMove.current = p;
    if (moveRaf.current === null) {
      moveRaf.current = requestAnimationFrame(() => {
        moveRaf.current = null;
        const q = lastMove.current;
        if (q) latest.current.onHover(infoAt(q.x, q.y));
      });
    }
  };

  const onPointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const p = local(e);
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) pinchRef.current = null;
    const drag = dragRef.current;
    dragRef.current = null;
    if (drag && drag.kind === "click" && !drag.moved && e.button === 0) {
      latest.current.onPick(infoAt(p.x, p.y), e.nativeEvent);
    }
  };

  return (
    <div ref={hostRef} className="relative h-full w-full overflow-hidden bg-[#8c8f94]" style={{ touchAction: "none" }} dir="ltr">
      <canvas ref={pdfCanvasRef} className="absolute left-0 top-0 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.2)]" style={{ transformOrigin: "0 0", pointerEvents: "none" }} />
      <canvas
        ref={overlayRef}
        className="absolute left-0 top-0 outline-none"
        style={{ cursor: spaceRef.current ? "grab" : cursor }}
        tabIndex={0}
        data-testid="takeoff-overlay"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onPointerLeave={() => latest.current.onHover(null)}
        onDoubleClick={(e) => {
          const p = local(e);
          latest.current.onDoubleClick(infoAt(p.x, p.y));
        }}
        onContextMenu={(e) => e.preventDefault()}
      />
    </div>
  );
});

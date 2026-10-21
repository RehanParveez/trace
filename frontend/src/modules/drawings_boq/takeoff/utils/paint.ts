import type { Draft, Tool } from "../store/takeoffView.store";
import type { AreaGeometry, CountGeometry, LengthGeometry, Pt, RegionPick, ScalePair, SnapKind, TakeoffMeasurement, WallPick } from "../types/takeoff.types";
import { dist, polygonArea, polylineLength } from "./geometry";
import { fmtMm } from "./format";
import type { PlanBox } from "./floorSources";
import type { ReadingGapsMark } from "../types/readingGaps.types";
import { applyMatrix } from "./viewport";
import type { Matrix } from "./viewport";

export interface HoverState { pt: Pt; snapKind: SnapKind | null; snapPt: Pt | null }

export interface Scene {
  measurements: TakeoffMeasurement[];
  selectedIds: Set<string>;
  showMeasurements: boolean;
  tool: Tool;
  draft: Draft | null;
  hover: HoverState | null;
  mmPerPt: number | null;
  wallPick: WallPick | null;
  wallTrim: [number, number];
  regionPick: RegionPick | null;
  calibrationPts: Pt[];
  rulerPts: Pt[];
  dimensionPairs: ScalePair[] | null;
  suggestionPts: Pt[];
  focusId: string | null;
  disabledNote: string | null;
  planBoxes?: PlanBox[];
  markColours?: Record<string, string>;
  readingGaps?: ReadingGapsMark[];
}

const PALETTE = ["#2f68a8", "#1e9d63", "#c24a3a", "#8a5cc2", "#d98a1f", "#1d9aa3", "#b0407e", "#6b7a1f"];

export function colourFor(key: string | null | undefined): string {
  if (!key) return "#6b6f76";
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

function path(ctx: CanvasRenderingContext2D, m: Matrix, pts: Pt[], closed: boolean): void {
  ctx.beginPath();
  pts.forEach((p, i) => {
    const [x, y] = applyMatrix(m, p[0], p[1]);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  if (closed) ctx.closePath();
}

function dot(ctx: CanvasRenderingContext2D, x: number, y: number, r: number, fill: string, stroke = "#fff"): void {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = stroke;
  ctx.stroke();
}

function label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, colour: string): void {
  ctx.font = "600 11px Inter, system-ui, sans-serif";
  const w = ctx.measureText(text).width + 10;
  ctx.fillStyle = "rgba(255,255,255,0.94)";
  ctx.strokeStyle = colour;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(x, y - 15, w, 18, 4);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#191410";
  ctx.fillText(text, x + 5, y - 2);
}

export function markerFor(ctx: CanvasRenderingContext2D, kind: SnapKind, x: number, y: number): void {
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#e0a100";
  ctx.fillStyle = "rgba(224,161,0,0.18)";
  const s = 7;
  ctx.beginPath();
  if (kind === "ENDPOINT") ctx.rect(x - s, y - s, s * 2, s * 2);
  else if (kind === "INTERSECTION") {
    ctx.moveTo(x - s, y - s);
    ctx.lineTo(x + s, y + s);
    ctx.moveTo(x + s, y - s);
    ctx.lineTo(x - s, y + s);
  } else if (kind === "MIDPOINT") {
    ctx.moveTo(x, y - s);
    ctx.lineTo(x + s, y + s);
    ctx.lineTo(x - s, y + s);
    ctx.closePath();
  } else ctx.arc(x, y, s - 1, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function drawMeasurement(ctx: CanvasRenderingContext2D, m: Matrix, meas: TakeoffMeasurement, selected: boolean, focused: boolean, override?: string): void {
  const colour = override ?? colourFor(meas.work_item_code ?? meas.kind);
  const confirmed = meas.status === "CONFIRMED";
  ctx.save();
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.strokeStyle = colour;
  ctx.fillStyle = colour + (confirmed ? "33" : "18");
  ctx.lineWidth = selected || focused ? 3.5 : 2;
  ctx.setLineDash(confirmed ? [] : [7, 4]);
  if (meas.kind === "LENGTH") {
    const g = meas.geometry as LengthGeometry;
    path(ctx, m, g.points, Boolean(g.closed));
    ctx.stroke();
    const mid = g.points[Math.floor(g.points.length / 2)];
    if (mid && (selected || focused)) g.points.forEach((p) => { const [x, y] = applyMatrix(m, p[0], p[1]); dot(ctx, x, y, 3.5, colour); });
  } else if (meas.kind === "AREA") {
    const g = meas.geometry as AreaGeometry;
    ctx.beginPath();
    for (const ring of [g.outer, ...(g.holes ?? [])]) {
      ring.forEach((p, i) => {
        const [x, y] = applyMatrix(m, p[0], p[1]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.closePath();
    }
    ctx.fill("evenodd");
    ctx.stroke();
  } else {
    const g = meas.geometry as CountGeometry;
    ctx.setLineDash([]);
    g.points.forEach((p) => {
      const [x, y] = applyMatrix(m, p[0], p[1]);
      ctx.beginPath();
      ctx.arc(x, y, selected || focused ? 8 : 6, 0, Math.PI * 2);
      ctx.fillStyle = colour + (confirmed ? "cc" : "66");
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#fff";
      ctx.stroke();
    });
  }
  ctx.restore();
}

function paintPlanBoxes(ctx: CanvasRenderingContext2D, m: Matrix, all: PlanBox[]): void {

  const boxes = [...all].sort((a, b) => Number(a.kind === "READ") - Number(b.kind === "READ"));
  ctx.save();
  ctx.lineJoin = "round";
  for (const b of boxes) {
    const [x0, y0, x1, y1] = b.bbox;
    const pts: Pt[] = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
    const read = b.kind === "READ";
    ctx.fillStyle = read ? "rgba(30,157,99,0.06)" : "rgba(90,96,104,0.16)";
    ctx.strokeStyle = read ? "#1e9d63" : "#6b6f76";
    ctx.lineWidth = read ? 2.5 : 1.5;
    ctx.setLineDash(read ? [] : [8, 5]);
    path(ctx, m, pts, true);
    ctx.fill();
    ctx.stroke();
  }
  ctx.setLineDash([]);
  for (const b of boxes) {
    const [x0, y0, x1, y1] = b.bbox;
    const sp = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map((p) => applyMatrix(m, p[0], p[1]));
    const left = Math.min(...sp.map((p) => p[0]));
    const top = Math.min(...sp.map((p) => p[1]));
    label(ctx, b.label, left + 4, top + 17, b.kind === "READ" ? "#1e9d63" : "#6b6f76");
  }
  ctx.restore();
}

export function paintScene(ctx: CanvasRenderingContext2D, m: Matrix, size: { w: number; h: number }, scene: Scene): void {
  if (scene.planBoxes && scene.planBoxes.length > 0) paintPlanBoxes(ctx, m, scene.planBoxes);
  if (scene.showMeasurements) {
     for (const meas of scene.measurements) drawMeasurement(ctx, m, meas, scene.selectedIds.has(meas.id), scene.focusId === meas.id, scene.markColours?.[meas.id]);
  }

  if (scene.readingGaps && scene.readingGaps.length > 0) {
    ctx.save();
    ctx.lineWidth = 2.5;
    ctx.setLineDash([5, 3]);
    for (const mk of scene.readingGaps) {
      const [x, y] = applyMatrix(m, mk.x, mk.y);
      ctx.beginPath();
      ctx.arc(x, y, 13, 0, Math.PI * 2);
      ctx.strokeStyle = mk.colour;
      ctx.fillStyle = mk.colour + "22";
      ctx.fill();
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const mk of scene.readingGaps) {
      const [x, y] = applyMatrix(m, mk.x, mk.y);
      label(ctx, mk.text, x + 15, y - 6, mk.colour);
    }
    ctx.restore();
  }

  if (scene.dimensionPairs) {
    ctx.save();
    ctx.lineWidth = 2;
    for (const p of scene.dimensionPairs) {
      const dev = Math.abs(p.deviation_pct ?? 0);
      const colour = !p.inlier ? "#8c806e" : dev <= 1 ? "#1e9d63" : dev <= 2 ? "#d98a1f" : "#c24a3a";
      const [x1, y1] = applyMatrix(m, p.p1[0], p.p1[1]);
      const [x2, y2] = applyMatrix(m, p.p2[0], p.p2[1]);
      ctx.strokeStyle = colour;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      label(ctx, `${p.text}${p.deviation_pct !== undefined ? `  ${p.deviation_pct >= 0 ? "+" : ""}${p.deviation_pct.toFixed(2)}%` : ""}`, (x1 + x2) / 2 + 6, (y1 + y2) / 2 - 4, colour);
    }
    ctx.restore();
  }

  if (scene.regionPick) {
    ctx.save();
    ctx.fillStyle = "rgba(47,104,168,0.18)";
    ctx.strokeStyle = "#2f68a8";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (const ring of [scene.regionPick.outer, ...scene.regionPick.holes.map((h) => h.ring)]) {
      ring.forEach((p, i) => {
        const [x, y] = applyMatrix(m, p[0], p[1]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.closePath();
    }
    ctx.fill("evenodd");
    ctx.stroke();
    ctx.restore();
  }

  if (scene.wallPick) {
    ctx.save();
    ctx.strokeStyle = "rgba(47,104,168,0.55)";
    ctx.lineWidth = 3;
    path(ctx, m, scene.wallPick.run, false);
    ctx.stroke();
    if (scene.wallPick.centreline && scene.wallPick.centreline.length >= 2) {
      const cl = scene.wallPick.centreline;
      const a = cl[0];
      const b = cl[cl.length - 1];
      const len = dist(a, b) || 1;
      const ux = (b[0] - a[0]) / len;
      const uy = (b[1] - a[1]) / len;
      const [t0, t1] = scene.wallTrim;
      const s: Pt = [a[0] + ux * t0, a[1] + uy * t0];
      const e: Pt = [b[0] - ux * t1, b[1] - uy * t1];
      ctx.strokeStyle = "#2f68a8";
      ctx.lineWidth = 3;
      ctx.setLineDash([9, 5]);
      path(ctx, m, [s, e], false);
      ctx.stroke();
      ctx.setLineDash([]);
      for (const p of [s, e]) { const [x, y] = applyMatrix(m, p[0], p[1]); dot(ctx, x, y, 4.5, "#2f68a8"); }
    }
    ctx.restore();
  }

  for (const p of scene.suggestionPts) {
    const [x, y] = applyMatrix(m, p[0], p[1]);
    ctx.beginPath();
    ctx.arc(x, y, 9, 0, Math.PI * 2);
    ctx.strokeStyle = "#d98a1f";
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }

  const d = scene.draft;
  if (d) {
    ctx.save();
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.strokeStyle = "#d98a1f";
    ctx.fillStyle = "rgba(217,138,31,0.18)";
    ctx.lineWidth = 2.5;
    const live = scene.hover ? (scene.hover.snapPt ?? scene.hover.pt) : null;
    const activeRing = d.activeHole !== null ? d.holes[d.activeHole] : d.points;
    const rubber = live && !d.closed && !d.origin && scene.tool !== "count" && activeRing.length > 0 ? [...activeRing, live] : activeRing;
    if (d.kind === "COUNT") {
      d.points.forEach((p, i) => { const [x, y] = applyMatrix(m, p[0], p[1]); dot(ctx, x, y, 7, "#d98a1f"); ctx.fillStyle = "#fff"; ctx.font = "700 9px Inter"; ctx.textAlign = "center"; ctx.fillText(String(i + 1), x, y + 3); ctx.textAlign = "start"; });
    } else if (d.kind === "AREA") {
      if (d.points.length >= 3 || (d.activeHole === null && rubber.length >= 3)) {
        ctx.beginPath();
        const ring0 = d.activeHole === null ? rubber : d.points;
        ring0.forEach((p, i) => { const [x, y] = applyMatrix(m, p[0], p[1]); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
        ctx.closePath();
        for (let h = 0; h < d.holes.length; h++) {
          const ring = d.activeHole === h ? rubber : d.holes[h];
          ring.forEach((p, i) => { const [x, y] = applyMatrix(m, p[0], p[1]); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
          ctx.closePath();
        }
        ctx.fill("evenodd");
      }
      path(ctx, m, d.activeHole === null ? rubber : d.points, d.closed || (d.activeHole !== null));
      ctx.stroke();
      for (let h = 0; h < d.holes.length; h++) {
        ctx.setLineDash([5, 4]);
        path(ctx, m, d.activeHole === h ? rubber : d.holes[h], d.activeHole !== h);
        ctx.stroke();
        ctx.setLineDash([]);
      }
      d.points.forEach((p) => { const [x, y] = applyMatrix(m, p[0], p[1]); dot(ctx, x, y, 4, "#d98a1f"); });
    } else {
      path(ctx, m, rubber, d.closed);
      ctx.stroke();
      d.points.forEach((p) => { const [x, y] = applyMatrix(m, p[0], p[1]); dot(ctx, x, y, 4, "#d98a1f"); });
    }
    if (live && scene.mmPerPt && activeRing.length > 0 && d.kind !== "COUNT" && !d.origin) {
      const [lx, ly] = applyMatrix(m, live[0], live[1]);
      const pts = [...activeRing, live];
      const text = d.kind === "LENGTH"
        ? `≈ ${fmtMm(polylineLength(pts, d.closed) * scene.mmPerPt)}`
        : pts.length >= 3 ? `≈ ${((polygonArea(pts) * scene.mmPerPt * scene.mmPerPt) / 1e6).toFixed(3)} m²` : "";
      if (text) label(ctx, text, lx + 14, ly - 8, "#d98a1f");
    }
    ctx.restore();
  }

  for (const [pts, colour] of [[scene.calibrationPts, "#c24a3a"], [scene.rulerPts, "#1d9aa3"]] as Array<[Pt[], string]>) {
    if (pts.length === 0) continue;
    ctx.save();
    ctx.strokeStyle = colour;
    ctx.lineWidth = 2.5;
    const live = scene.hover && pts.length === 1 ? (scene.hover.snapPt ?? scene.hover.pt) : null;
    const line = live ? [...pts, live] : pts;
    path(ctx, m, line, false);
    ctx.stroke();
    pts.forEach((p) => { const [x, y] = applyMatrix(m, p[0], p[1]); dot(ctx, x, y, 5, colour); });
    if (line.length === 2 && scene.mmPerPt) {
      const [x, y] = applyMatrix(m, (line[0][0] + line[1][0]) / 2, (line[0][1] + line[1][1]) / 2);
      label(ctx, fmtMm(dist(line[0], line[1]) * scene.mmPerPt), x + 8, y - 8, colour);
    }
    ctx.restore();
  }

  if (scene.hover?.snapKind && scene.hover.snapPt) {
    const [x, y] = applyMatrix(m, scene.hover.snapPt[0], scene.hover.snapPt[1]);
    markerFor(ctx, scene.hover.snapKind, x, y);
    ctx.font = "600 10px Inter, system-ui, sans-serif";
    ctx.fillStyle = "#7a5a00";
    ctx.fillText(scene.hover.snapKind.toLowerCase(), x + 10, y + 18);
  }

  if (scene.disabledNote) {
    ctx.save();
    ctx.font = "600 12px Inter, system-ui, sans-serif";
    const w = ctx.measureText(scene.disabledNote).width + 16;
    ctx.fillStyle = "rgba(194,74,58,0.92)";
    ctx.fillRect(size.w / 2 - w / 2, 12, w, 24);
    ctx.fillStyle = "#fff";
    ctx.fillText(scene.disabledNote, size.w / 2 - w / 2 + 8, 28);
    ctx.restore();
  }
}

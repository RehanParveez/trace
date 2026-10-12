import type { Pt, TextWord } from "../types/takeoff.types";

export interface PdfTextItem { str: string; transform: number[]; width: number; height: number }

export interface AlignmentResult {
  state: "ALIGNED" | "MISALIGNED" | "UNVERIFIED";
  checked: number;
  matched: number;
  maxErrorPt: number;
}

export function pdfItemCentre(item: PdfTextItem): Pt {
  const [a, b, c, d, e, f] = item.transform;
  const lenU = Math.hypot(a, b) || 1;
  const lenV = Math.hypot(c, d) || 1;
  const ux = a / lenU;
  const uy = b / lenU;
  const vx = c / lenV;
  const vy = d / lenV;
  const along = (item.width || 0) / 2;
  const up = lenV * 0.3;
  return [e + ux * along + vx * up, f + uy * along + vy * up];
}

export function checkAlignment(backend: TextWord[], items: PdfTextItem[], sampleMax = 14): AlignmentResult {
  const norm = (s: string) => s.trim().toUpperCase();
  const pdfBy = new Map<string, Pt[]>();
  for (const it of items) {
    const key = norm(it.str);
    if (key.length < 2 || key.includes(" ")) continue;
    (pdfBy.get(key) ?? pdfBy.set(key, []).get(key)!).push(pdfItemCentre(it));
  }
  const backBy = new Map<string, TextWord[]>();
  for (const w of backend) {
    const key = norm(w.text);
    if (key.length < 2) continue;
    (backBy.get(key) ?? backBy.set(key, []).get(key)!).push(w);
  }
  const keys = [...backBy.keys()].filter((k) => pdfBy.has(k) && backBy.get(k)!.length === pdfBy.get(k)!.length);
  keys.sort((a, b) => (backBy.get(a)!.length - backBy.get(b)!.length) || (a < b ? -1 : 1));
  const picks: Array<{ w: TextWord; centres: Pt[] }> = [];
  for (const k of keys) {
    for (const w of backBy.get(k)!) picks.push({ w, centres: pdfBy.get(k)! });
    if (picks.length >= sampleMax * 3) break;
  }
 
  picks.sort((p, q) => p.w.x - q.w.x);
  const step = Math.max(1, Math.floor(picks.length / sampleMax));
  const sample = picks.filter((_, i) => i % step === 0).slice(0, sampleMax);
  let matched = 0;
  let maxErr = 0;
  for (const { w, centres } of sample) {
    let best = Infinity;
    for (const c of centres) best = Math.min(best, Math.hypot(c[0] - w.x, c[1] - w.y));
    const tol = Math.max(4, w.size * 1.0);
    if (best <= tol) matched++;
    maxErr = Math.max(maxErr, Math.min(best, 1e6));
  }
  if (sample.length < 3) return { state: "UNVERIFIED", checked: sample.length, matched, maxErrorPt: maxErr };
  return { state: matched / sample.length >= 0.7 ? "ALIGNED" : "MISALIGNED", checked: sample.length, matched, maxErrorPt: maxErr };
}

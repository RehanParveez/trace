import type { CandidateCategory, TakeoffCandidate, TypedValue } from "../types/takeoff.types";
import { CATEGORY_TEXT, fieldsStillNeeded, kindKey, SITE_TEXT } from "./candidates";
import type { HeightField, SiteKind } from "./candidates";

export interface Offer { mm: number; kinds: string[]; times: number }

function kindName(key: string): string {
  if (key in SITE_TEXT) return SITE_TEXT[key as SiteKind];
  if (key in CATEGORY_TEXT) return CATEGORY_TEXT[key as CandidateCategory].one;
  return key.charAt(0) + key.slice(1).toLowerCase().replace(/_/g, " ");
}

export function offersFor(field: HeightField, items: TakeoffCandidate[], memory: TypedValue[] | undefined, picks?: Record<string, string>): Offer[] {
  if (!memory?.length) return [];
  const kinds = new Set(items.filter((c) => fieldsStillNeeded(c, picks).includes(field)).map((c) => String(kindKey(c))));
  const out: Offer[] = [];
  for (const m of memory) {
    if (m.field !== field || !kinds.has(m.kind)) continue;
    const same = out.find((o) => o.mm === m.value_mm);
    if (same) {
      if (!same.kinds.includes(kindName(m.kind))) same.kinds.push(kindName(m.kind));
      same.times += m.times;
    } else {
      out.push({ mm: m.value_mm, kinds: [kindName(m.kind)], times: m.times });
    }
  }
  return out;
}

export function offerText(o: Offer): string {
  const mm = Number.isInteger(o.mm) ? String(o.mm) : o.mm.toFixed(1);
  return `${mm} mm · ${o.kinds.join(", ")}${o.times > 1 ? ` · used ${o.times} times` : ""}`;
}

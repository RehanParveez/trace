import type { DerivedStats } from "../types/drawings-boq.types";

export interface EarthBalanceView {
  excavationM3: string;
  backfillM3: string;
  cartedM3: string;
  closes: boolean;
}

export interface EarthFillView {
  fillM3: string;
  needLooseM3: string;
  surplusLooseM3: string;
  reusedM3: string;
  importedM3: string;
  cartedLooseM3: string;
  reuseOn: boolean;
  assumed: string[];
}

export function earthBalanceView(stats: DerivedStats | null | undefined): EarthBalanceView | null {
  const b = stats?.balance;
  if (!b) return null;
  return { excavationM3: String(b.excavation_m3), backfillM3: String(b.backfill_m3), cartedM3: String(b.carted_m3), closes: Boolean(b.closes) };
}

export function earthFillView(stats: DerivedStats | null | undefined): EarthFillView | null {
  const b = stats?.balance;
  if (!b || b.fill_note !== "FILL_REPORTED") return null;
  return {
    fillM3: String(b.floor_fill_m3 ?? "0"),
    needLooseM3: String(b.floor_fill_need_m3 ?? "0"),
    surplusLooseM3: String(b.surplus_loose_m3 ?? "0"),
    reusedM3: String(b.fill_reused_m3 ?? "0"),
    importedM3: String(b.fill_imported_m3 ?? "0"),
    cartedLooseM3: String(b.carted_loose_m3 ?? "0"),
    reuseOn: Boolean(b.fill_reuse_on),
    assumed: Array.isArray(b.fill_assumed) ? b.fill_assumed : [],
  };
}

export interface FloorWorksView {
  ran: boolean;
  reason: string | null;
  areaM2: string;
  rooms: number;
  levelAssumed: boolean;
  skipped: { code: string; why: string }[];
}

export function floorWorksView(stats: DerivedStats | null | undefined): FloorWorksView | null {
  const fw = stats?.floor_works;
  if (!fw || !fw.enabled) return null;
  return {
    ran: Boolean(fw.ran),
    reason: fw.reason ?? null,
    areaM2: String(fw.area_m2 ?? "0"),
    rooms: Number(fw.rooms ?? 0),
    levelAssumed: fw.level_how === "LOWEST_MEMBERS",
    skipped: Object.entries(fw.skipped ?? {}).map(([code, why]) => ({ code, why: String(why) })),
  };
}

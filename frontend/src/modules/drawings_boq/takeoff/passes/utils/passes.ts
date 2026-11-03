import type { ElectricalReason, TankKind, TankRecord, TankSource } from "../types/passes.types";

export type Basis = "DRAWING" | "TYPED" | "ASSUMED";

const PRINTED_ROUTES = ["DETAIL", "LABEL", "DETAIL_PICTURE", "WALLS"];

export function basisOfRoute(route: string | undefined): Basis {
  if (route === "DECISION") return "TYPED";
  return route && PRINTED_ROUTES.includes(route) ? "DRAWING" : "ASSUMED";
}

export const BASIS_TEXT: Record<Basis, string> = {
  DRAWING: "Read from the drawing",
  TYPED: "Typed by you",
  ASSUMED: "Assumed: the drawing does not print it",
};

export const TANK_TEXT: Record<TankKind, string> = {
  OHWT: "Over-head water tank",
  UGWT: "Underground water tank",
  SEPTIC: "Septic tank",
};

export const REASON_TEXT: Record<ElectricalReason, string> = {
  NOT_COUNTABLE: "The legend picture has fewer than three drawn objects and no text tag, so there is nothing to match on the plans.",
  TAG_NOT_ON_PLAN: "The legend symbol is a text tag and the tag is not on the plan pages.",
  NO_PLAN_HIT: "The legend picture was searched on the plans and no run of drawn objects of the same sizes and layout was found.",
};

export function metres(mm: number | null | undefined): string {
  return typeof mm === "number" && Number.isFinite(mm) ? `${(mm / 1000).toFixed(3)} m` : "-";
}

export function planText(t: TankRecord): string {
  return `${metres(t.plan_mm[0])} x ${metres(t.plan_mm[1])}`;
}

export function sourceTitle(s: TankSource | undefined): string {
  if (!s) return "";
  const page = s.page_no ? `page ${s.page_no}: ` : "";
  return `${page}${s.text || s.route.toLowerCase().replace(/_/g, " ")}`;
}

export function pagesList(pages: number[] | undefined): string {
  return (pages ?? []).join(", ");
}

export function sizeValid(value: string): boolean {
  const parts = value.trim().split(/\s*[xX,]\s*/).filter((p) => p.length > 0);
  return (parts.length === 2 || parts.length === 4) && parts.every((p) => Number.isFinite(Number(p)) && Number(p) > 0);
}

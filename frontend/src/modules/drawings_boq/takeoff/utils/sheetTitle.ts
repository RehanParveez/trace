import type { TakeoffSheet } from "../types/takeoff.types";

export function sheetTitle(sheet: TakeoffSheet): string {
  return sheet.label?.trim() || `Sheet ${sheet.page_no}`;
}
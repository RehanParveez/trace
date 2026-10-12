const TO_MM: Record<string, number> = { mm: 1, cm: 10, m: 1000, ft: 304.8, in: 25.4 };

function unitOf(raw: string | undefined): keyof typeof TO_MM | null {
  if (!raw) return null;
  const u = raw.toLowerCase();
  if (u === "mm") return "mm";
  if (u === "cm") return "cm";
  if (u === "m" || u === "meter" || u === "meters" || u === "metre" || u === "metres") return "m";
  if (u === "ft" || u === "feet" || u === "foot" || u === "'" || u === "’") return "ft";
  if (u === "in" || u === "inch" || u === "inches" || u === '"' || u === "”") return "in";
  return null;
}

export function parseLengthMm(text: string): number | null {
  const s = text.trim();
  if (!s) return null;
  const re = /(\d+(?:\.\d+)?)\s*(mm|cm|meters?|metres?|m|feet|foot|ft|inches|inch|in|'|’|"|”)?/gi;
  let total = 0;
  let any = false;
  let sawFeet = false;
  let consumed = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s)) !== null) {
    if (s.slice(consumed, m.index).replace(/[\s,-]/g, "") !== "") return null;
    consumed = m.index + m[0].length;
    const value = Number(m[1]);
    let unit = unitOf(m[2]);
    if (!unit) unit = sawFeet ? "in" : "mm";
    if (unit === "ft") sawFeet = true;
    total += value * TO_MM[unit];
    any = true;
  }
  if (!any || s.slice(consumed).replace(/[\s,-]/g, "") !== "") return null;
  return Math.round(total * 1000) / 1000;
}

export function mmToString(mm: number): string {
  return String(Math.round(mm * 1000) / 1000);
}
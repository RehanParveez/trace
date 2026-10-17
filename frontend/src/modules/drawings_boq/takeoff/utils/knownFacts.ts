import type { FactResult, FactsCheck, KnownFact } from "../types/takeoff.types";

export interface ParsedFacts { facts: KnownFact[]; errors: Array<{ line: number; message: string }> }

const NUM = /^\d+(?:\.\d+)?$/;

function num(word: string | undefined): number | null {
  return word !== undefined && NUM.test(word) ? Number(word) : null;
}

function parseLine(words: string[]): KnownFact | string {
  const head = words[0].toLowerCase();
  const rest = words.slice(1);
  if (head === "total") {
    const category = rest[0];
    const count = num(rest[1]);
    if (!category || count === null || !Number.isInteger(count)) return "Write it as: total door 30 (and a floor at the end for one floor).";
    return { kind: "TOTAL", category: category.toUpperCase(), count, ...(rest[2] ? { floor: rest[2] } : {}) };
  }
  if (head === "count") {
    const [category, tag] = rest;
    const count = num(rest[2]);
    if (!category || !tag || count === null || !Number.isInteger(count)) return "Write it as: count column C1 10 ground (the mark, the number, and a floor if you like).";
    return { kind: "COUNT", category: category.toUpperCase(), tag: tag.toUpperCase(), count, ...(rest[3] ? { floor: rest[3] } : {}) };
  }
  if (head === "room") {
    const area = rest.findIndex((w) => num(w) !== null);
    if (area < 1) return "Write it as: room LOUNGE 18.5 ground (the name as the plan prints it, then the area in square metres).";
    const floor = rest[area + 1];
    return { kind: "ROOM_AREA", name: rest.slice(0, area).join(" "), area_m2: Number(rest[area]), ...(floor ? { floor } : {}) };
  }
  if (head === "slab") {
    const area = num(rest[1]);
    if (!rest[0] || area === null) return "Write it as: slab ground 120.4 (the floor, then the covered area in square metres).";
    return { kind: "SLAB_AREA", floor: rest[0], area_m2: area };
  }
  if (head === "schedule") {
    if (!rest[0]) return "Write it as: schedule D1 900 2100 (the mark, then width and height in mm).";
    const w = num(rest[1]);
    const h = num(rest[2]);
    if ((rest[1] && w === null) || (rest[2] && h === null)) return "The width and height of a schedule row are numbers in mm.";
    return { kind: "SCHEDULE", mark: rest[0].toUpperCase(), ...(w !== null ? { width_mm: w } : {}), ...(h !== null ? { height_mm: h } : {}) };
  }
  return "A line starts with total, count, room, slab or schedule.";
}

export function parseFacts(text: string): ParsedFacts {
  const facts: KnownFact[] = [];
  const errors: ParsedFacts["errors"] = [];
  text.split(/\r?\n/).forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    const got = parseLine(line.split(/\s+/));
    if (typeof got === "string") errors.push({ line: i + 1, message: got });
    else facts.push(got);
  });
  return { facts, errors };
}

export function factsLine(data: FactsCheck | undefined): string {
  if (!data || !data.results.length) return "";
  const bits: string[] = [];
  if (data.failed) bits.push(data.failed === 1 ? "1 read differently" : `${data.failed} read differently`);
  if (data.missing) bits.push(data.missing === 1 ? "1 not read" : `${data.missing} not read`);
  if (data.passed) bits.push(data.passed === 1 ? "1 as printed" : `${data.passed} as printed`);
  return bits.join(" · ");
}

export function factTone(status: FactResult["status"]): "green" | "red" | "gold" {
  return status === "PASS" ? "green" : status === "FAIL" ? "red" : "gold";
}

export function factLabel(status: FactResult["status"]): string {
  return status === "PASS" ? "As printed" : status === "FAIL" ? "Read differently" : "Not read";
}

export function sortedResults(results: FactResult[]): FactResult[] {
  const rank = { FAIL: 0, MISSING: 1, PASS: 2 } as const;
  return [...results].sort((a, b) => rank[a.status] - rank[b.status] || a.index - b.index);
}

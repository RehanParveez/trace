export type NoteScope = "ROW" | "SHEET" | "DRAWING";

export interface ScopedIssue {
  code?: string;
  severity?: string;
  message?: string;
  scope?: string | null;
}

export interface Condition {
  scope: NoteScope;
  code: string;
  severity: string;
  message: string;
  rows: number;
  sheets: number[];
}

export function scopeOf(issue: unknown): NoteScope {
  const scope = (issue as ScopedIssue | null)?.scope;
  return scope === "SHEET" || scope === "DRAWING" ? scope : "ROW";
}

export function rowIssues(issues: unknown[] | null | undefined): ScopedIssue[] {
  return (issues ?? []).filter((i): i is ScopedIssue => typeof i === "object" && i !== null && scopeOf(i) === "ROW");
}

interface RowLike {
  normalization_issues?: unknown[];
  properties?: Record<string, unknown>;
}

export function conditionsOf(rows: RowLike[]): Condition[] {
  const found = new Map<string, Condition>();
  for (const row of rows) {
    const pdf = (row.properties?._pdf ?? {}) as { page_no?: number };
    for (const raw of row.normalization_issues ?? []) {
      const issue = raw as ScopedIssue;
      const scope = scopeOf(issue);
      if (scope === "ROW" || !issue.code) continue;
      const key = `${scope}|${issue.code}`;
      const slot = found.get(key) ?? { scope, code: issue.code, severity: issue.severity ?? "info", message: issue.message ?? "", rows: 0, sheets: [] };
      slot.rows += 1;
      if (typeof pdf.page_no === "number" && !slot.sheets.includes(pdf.page_no)) slot.sheets.push(pdf.page_no);
      found.set(key, slot);
    }
  }
  return [...found.values()]
    .map((c) => ({ ...c, sheets: [...c.sheets].sort((a, b) => a - b) }))
    .sort((a, b) => (a.scope === b.scope ? b.rows - a.rows : a.scope === "SHEET" ? -1 : 1));
}

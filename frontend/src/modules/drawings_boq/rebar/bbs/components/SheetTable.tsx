import { useTranslation } from "react-i18next";
import { Badge } from "../../../../organizations/components/OrganizationUi";
import { kgPlain, signedKg } from "../utils/bbsReport";
import type { ReportSheet, ReportSummary } from "../types/bbsReport.types";

interface SheetTableProps {
  sheets: ReportSheet[];
  unassigned: ReportSummary["unassigned"];
  selected: number | null;
  onSelect: (idx: number | null) => void;
}

const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function SheetTable({ sheets, unassigned, selected, onSelect }: SheetTableProps) {
  const { t } = useTranslation();
  return (
    <div className="overflow-x-auto" data-testid="bbs-sheet-table">
      <table className="w-full min-w-[720px] text-left">
        <thead><tr>
          <th className={th}>{t("bbs.sheet.name", "Sheet")}</th>
          <th className={th}>{t("bbs.sheet.pages", "Pages")}</th>
          <th className={`${th} text-right`}>{t("bbs.sheet.printed", "Printed total kg")}</th>
          <th className={`${th} text-right`}>{t("bbs.sheet.computed", "Recomputed kg")}</th>
          <th className={`${th} text-right`}>{t("bbs.sheet.expected", "Expected kg")}</th>
          <th className={`${th} text-right`}>{t("bbs.sheet.findings", "Findings")}</th>
        </tr></thead>
        <tbody>
          {sheets.map((s) => (
            <tr key={s.idx} className={`cursor-pointer border-t border-[var(--color-border)] transition hover:bg-[var(--color-surface-muted)] ${selected === s.idx ? "bg-[var(--color-surface-muted)]" : ""}`}
              onClick={() => onSelect(selected === s.idx ? null : s.idx)}>
              <td className="px-3 py-2 text-[12.5px] text-[var(--color-text-primary)]">{s.name}</td>
              <td className="px-3 py-2 font-mono text-[12px] text-[var(--color-text-secondary)]">{s.first_page === s.last_page ? s.first_page : `${s.first_page}–${s.last_page}`}</td>
              <td className="px-3 py-2 text-right font-mono text-[12px]">{kgPlain(s.printed_total_kg)}</td>
              <td className="px-3 py-2 text-right font-mono text-[12px]">
                {kgPlain(s.computed_kg)}
                {s.printed_diff_kg !== null && Number(s.printed_diff_kg) !== 0 ? <span className="ml-1 text-[var(--color-warning)]">({signedKg(s.printed_diff_kg)})</span> : null}
              </td>
              <td className="px-3 py-2 text-right font-mono text-[12px]">{kgPlain(s.expected_kg)}</td>
              <td className="px-3 py-2 text-right text-[12px]">
                {s.findings}
                {s.open_findings > 0 ? <span className="ml-1"><Badge tone="gold">{t("bbs.sheet.open", "{{n}} open", { n: s.open_findings })}</Badge></span> : null}
              </td>
            </tr>
          ))}
          {unassigned.findings > 0 ? (
            <tr className="border-t border-[var(--color-border)] text-[var(--color-text-muted)]">
              <td className="px-3 py-2 text-[12px]" colSpan={4}>{t("bbs.sheet.loose", "Findings that belong to no single sheet")}</td>
              <td className="px-3 py-2 text-right font-mono text-[12px]">{signedKg(unassigned.effect_kg)}</td>
              <td className="px-3 py-2 text-right text-[12px]">{unassigned.findings}</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

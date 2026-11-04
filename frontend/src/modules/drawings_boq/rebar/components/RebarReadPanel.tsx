import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import { formatDiffKg, formatKg, pageRange, parseBbsRead, unreconciledSheets } from "../utils/bbsRead";

interface RebarReadPanelProps {
  meta: Record<string, unknown> | null | undefined;
}

const th = "px-3 py-2 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";
const MAX_UNREAD_SHOWN = 10;

export function RebarReadPanel({ meta }: RebarReadPanelProps) {
  const { t } = useTranslation();
  const read = parseBbsRead(meta);
  if (!read) return null;
  const off = unreconciledSheets(read);

  return (
    <div className="space-y-2.5 rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3" data-testid="bbs-read-panel">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12.5px] font-semibold text-[var(--color-text-primary)]">{t("rebar.read.title", "Read as a feet-and-inches bar schedule")}</span>
        <Badge tone="blue">{t("rebar.read.rows", "{{n}} rows", { n: read.row_count })}</Badge>
        <Badge tone="blue">{t("rebar.read.sheets", "{{n}} sheets", { n: read.sheet_count })}</Badge>
        {off.length === 0
          ? <Badge tone="green">{t("rebar.read.allMatch", "Every sheet matches its printed total")}</Badge>
          : <Badge tone="red">{t("rebar.read.someOff", "{{n}} sheet(s) do not match their printed total", { n: off.length })}</Badge>}
      </div>

      <div className="flex flex-wrap gap-x-6 font-mono text-[12px] text-[var(--color-text-secondary)]">
        <span>{t("rebar.read.printed", "printed total")}: {formatKg(read.printed_total_kg)} kg</span>
        <span>{t("rebar.read.readTotal", "rows add to")}: {formatKg(read.rows_total_kg)} kg</span>
      </div>

      {read.dropped_repeats.length > 0 ? (
        <p className="text-[12px] text-[var(--color-text-secondary)]">
          {t("rebar.read.repeats", "{{n}} row(s) printed again at the top of the next page were read once.", { n: read.dropped_repeats.length })}
        </p>
      ) : null}

      {read.unread_count > 0 ? (
        <div className="rounded-[7px] border border-[var(--color-border)] bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">
          <div className="font-semibold">{t("rebar.read.unread", "{{n}} line(s) on the pages were not read. Check them against the PDF.", { n: read.unread_count })}</div>
          <ul className="mt-1 list-disc ps-5">
            {read.unread_lines.slice(0, MAX_UNREAD_SHOWN).map((u, i) => (
              <li key={`${u.page}-${u.y}-${i}`}>{t("rebar.read.page", "page")} {u.page}: {u.text}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <details>
        <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-text-secondary)]">{t("rebar.read.bySheet", "Sheet by sheet")}</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left">
            <thead><tr>
              <th className={th}>{t("rebar.read.colSheet", "Sheet")}</th>
              <th className={th}>{t("rebar.read.colPages", "Pages")}</th>
              <th className={`${th} text-right`}>{t("rebar.read.colRows", "Rows")}</th>
              <th className={`${th} text-right`}>{t("rebar.read.colPrinted", "Printed kg")}</th>
              <th className={`${th} text-right`}>{t("rebar.read.colRead", "Read kg")}</th>
              <th className={`${th} text-right`}>{t("rebar.read.colDiff", "Difference")}</th>
            </tr></thead>
            <tbody>
              {read.sheets.map((s) => (
                <tr key={`${s.name}-${s.first_page}`} className="border-t border-[var(--color-border)]">
                  <td className="px-3 py-2 text-[12.5px] text-[var(--color-text-primary)]">{s.name}</td>
                  <td className="px-3 py-2 font-mono text-[12px]">{pageRange(s)}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{s.rows}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{formatKg(s.printed_total_kg)}</td>
                  <td className="px-3 py-2 text-right font-mono text-[12px]">{formatKg(s.computed_kg)}</td>
                  <td className={`px-3 py-2 text-right font-mono text-[12px] ${s.reconciled ? "" : "font-semibold text-[var(--color-danger)]"}`}>{formatDiffKg(s.diff_kg)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

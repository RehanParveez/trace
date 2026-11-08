import { useTranslation } from "react-i18next";
import { Badge, TableShell } from "../../../../organizations/components/OrganizationUi";
import type { BillingProfileOption, FlowBoq as FlowBoqData, ProfileSource, RateBookOption } from "../types/flow.types";
import { LINE_TONE, moneyOrDash, rangeText, SOURCE_TEXT } from "../utils/flow";

interface FlowBoqProps {
  data: FlowBoqData;
  profiles: BillingProfileOption[];
  profile: string | null;
  profileSource: ProfileSource;
  books: RateBookOption[];
  bookId: string | null;
  onProfile: (id: string | null) => void;
  onBook: (id: string | null) => void;
}

export function FlowBoq({ data, profiles, profile, profileSource, books, bookId, onProfile, onBook }: FlowBoqProps) {
  const { t } = useTranslation();
  const totals = data.totals;
  return (
    <div className="space-y-3" data-testid="flow-boq-view">
      <div className="flex flex-wrap items-center gap-3 text-[12.5px]">
        <label className="flex items-center gap-1.5">
          {t("boq.flow.profile", "Billing profile")}
          <select className="rounded border border-[var(--color-border)] px-2 py-1" value={profile ?? ""} onChange={(e) => onProfile(e.target.value || null)} data-testid="flow-profile">
            <option value="">{t("boq.flow.companyProfile", "Company's profile")}</option>
            {profiles.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </label>
        <span className="text-[var(--color-text-muted)]">{data.profile}: {SOURCE_TEXT[profileSource]}</span>
        <label className="ml-auto flex items-center gap-1.5">
          {t("boq.flow.rateBook", "Rate book")}
          <select className="rounded border border-[var(--color-border)] px-2 py-1" value={bookId ?? ""} onChange={(e) => onBook(e.target.value || null)} data-testid="flow-book">
            <option value="">{t("boq.flow.defaultStack", "Default stack")}</option>
            {books.map((b) => <option key={b.id} value={b.id}>{b.code}{b.name ? ` · ${b.name}` : ""}</option>)}
          </select>
        </label>
      </div>
      {data.rate_books.length > 0 ? <p className="text-[12px] text-[var(--color-text-muted)]">{t("boq.flow.pricedFrom", "Priced from")} {data.rate_books.map((b) => `${b.code} v${b.version}`).join(", ")}</p> : null}
      {data.banner.map((line) => <p key={line} className="text-[12.5px] font-semibold text-[var(--color-warning)]" data-testid="flow-banner">{line}</p>)}
      {data.rate_notes.map((line) => <p key={line} className="text-[12px] text-[var(--color-text-muted)]">{line}</p>)}
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label={t("boq.flow.total", "Total of priced lines")} value={moneyOrDash(totals.grand)} />
        <Stat label={t("boq.flow.measured", "Measured")} value={moneyOrDash(totals.measured)} />
        <Stat label={t("boq.flow.assumed", "Assumed")} value={moneyOrDash(totals.assumed)} />
        <Stat label={t("boq.flow.range", "Range of the lines that have one")} value={totals.range && totals.range.low !== null && totals.range.high !== null ? `${moneyOrDash(totals.range.low)} to ${moneyOrDash(totals.range.high)}` : "-"} />
      </div>
      {data.lines.length === 0 ? (
        <p className="text-[12.5px] text-[var(--color-text-muted)]">{t("boq.flow.noLines", "No line is billed yet. Read the drawings and calculate the quantities first.")}</p>
      ) : (
        <TableShell>
          <table className="w-full min-w-[900px] text-left text-[12.5px]" data-testid="flow-boq-table">
            <thead className="bg-[var(--color-surface-muted)] text-[11px] uppercase text-[var(--color-text-muted)]">
              <tr>
                <th className="px-3 py-2">{t("boq.flow.colItem", "Item")}</th>
                <th className="px-3 py-2">{t("boq.flow.colFloor", "Floor")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.colQty", "Quantity")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.colRate", "Rate")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.colAmount", "Amount")}</th>
                <th className="px-3 py-2">{t("boq.flow.colState", "State")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.colMeasured", "Measured")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.colAssumed", "Assumed")}</th>
                <th className="px-3 py-2">{t("boq.flow.colRange", "Range")}</th>
                <th className="px-3 py-2 text-right">{t("boq.flow.colOpen", "Open rows")}</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l, n) => (
                <tr key={`${l.code}-${l.floor ?? ""}-${n}`} className="border-t border-[var(--color-border)]" data-testid={`flow-line-${l.code}`}>
                  <td className="px-3 py-2">
                    <div className="font-semibold">{l.code}</div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">{l.unpriced_why ?? l.description}</div>
                  </td>
                  <td className="px-3 py-2">{l.floor ?? "-"}</td>
                  <td className="px-3 py-2 text-right font-mono">{l.qty ?? "-"} {l.unit}</td>
                  <td className="px-3 py-2 text-right font-mono">{moneyOrDash(l.rate)}</td>
                  <td className="px-3 py-2 text-right font-mono">{moneyOrDash(l.amount)}</td>
                  <td className="px-3 py-2"><Badge tone={LINE_TONE[l.state]}>{l.label}</Badge></td>
                  <td className="px-3 py-2 text-right font-mono">{moneyOrDash(l.measured_amount)}</td>
                  <td className="px-3 py-2 text-right font-mono">{moneyOrDash(l.assumed_amount)}</td>
                  <td className="px-3 py-2 font-mono">{rangeText(l)}</td>
                  <td className="px-3 py-2 text-right font-mono">{l.open_rows || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
      <div className="text-[11px] uppercase text-[var(--color-text-muted)]">{label}</div>
      <div className="font-mono text-[14px] font-semibold">{value}</div>
    </div>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, StatCard } from "../../../organizations/components/OrganizationUi";
import { pricedApi } from "../api/priced.api";
import { usePriced } from "../hooks/usePriced";
import { useRateBooks } from "../hooks/usePricing";

interface ProjectPricedPanelProps {
  projectId: string;
}

const money = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const qty = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: 3 }));

export function ProjectPricedPanel({ projectId }: ProjectPricedPanelProps) {
  const { t } = useTranslation();
  const [profile, setProfile] = useState("PRIVATE_QS");
  const [bookId, setBookId] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const books = useRateBooks({ status: "ACTIVE", owner: "all" });
  const query = usePriced(projectId, profile, bookId);
  const view = query.data;

  async function download() {
    setBusy(true);
    setFailed(false);
    try {
      const blob = await pricedApi.xlsx(projectId, profile, bookId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `priced-boq-${profile}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const selectClass = "rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-[13px]";

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("priced.panel.eyebrow", "PRICED BOQ")}
        title={t("priced.panel.title", "Priced from the measured quantities")}
        description={t(
          "priced.panel.desc",
          "Each bill line times its rate. A line with no rate stays unpriced and says why; no rate is ever made up, and no quantity is changed.",
        )}
        action={
          <div className="flex flex-wrap items-center gap-2">
            {view ? (
              <select className={selectClass} value={profile} onChange={(e) => setProfile(e.target.value)} aria-label={t("billing.panel.profile", "Billing method")}>
                {view.profiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            ) : null}
            <select className={selectClass} value={bookId} onChange={(e) => setBookId(e.target.value)} aria-label={t("priced.panel.book", "Rate book")}>
              <option value="">{t("priced.panel.stack", "Rate books in force")}</option>
              {books.books.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.code} v{b.immutable_version}
                </option>
              ))}
            </select>
            <Button variant="primary" size="sm" onClick={() => void download()} disabled={busy || !view?.has_ledger}>
              {t("priced.panel.download", "Download workbook")}
            </Button>
          </div>
        }
      />

      {query.isLoading ? (
        <LoadingState label={t("priced.panel.loading", "Pricing the quantities…")} />
      ) : query.isError || !view ? (
        <div className="p-5">
          <ErrorState title={t("priced.panel.loadError", "We couldn't price the quantities")} onRetry={() => void query.refetch()} />
        </div>
      ) : !view.has_ledger ? (
        <div className="p-5">
          <EmptyState title={t("billing.panel.noLedger", "No first-upload reading yet")} description={t("priced.panel.noLedgerBody", "Run the first-upload job on this project's drawings, then price it.")} />
        </div>
      ) : (
        <div className="space-y-5 p-5">
          {failed ? <div className="text-[12.5px] text-[var(--color-danger)]">{t("priced.panel.downloadFailed", "The workbook could not be built.")}</div> : null}
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label={t("priced.panel.statTotal", "Total of priced lines")} value={money(view.totals.grand)} note={t("priced.panel.statTotalNote", "{{n}} lines priced", { n: view.totals.priced })} icon="budget" tone="blue" />
            <StatCard
              label={t("priced.panel.statAssumed", "Of which assumed")}
              value={money(view.totals.assumed)}
              note={t("priced.panel.statAssumedNote", "{{m}} rests on measured quantities", { m: money(view.totals.measured) })}
              icon={view.totals.assumed > 0 ? "alert" : "check"}
              tone={view.totals.assumed > 0 ? "gold" : "green"}
            />
            <StatCard
              label={t("priced.panel.statUnpriced", "Lines not priced")}
              value={view.totals.unpriced}
              note={view.totals.unpriced > 0 ? t("priced.panel.unpricedNote", "Not in the total; each shows why") : t("priced.panel.pricedNote", "Every line has a rate")}
              icon={view.totals.unpriced > 0 ? "alert" : "check"}
              tone={view.totals.unpriced > 0 ? "gold" : "green"}
            />
          </div>

          {view.totals.range ? (
            <div className="text-[12.5px] text-[var(--color-text-secondary)]">
              {t("priced.panel.range", "Lines with a quantity range: {{low}} to {{high}} against {{of}}.", { low: money(view.totals.range.low), high: money(view.totals.range.high), of: money(view.totals.range.of_amount) })}
            </div>
          ) : null}

          {view.rate_books.length === 0 ? (
            <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[13px]">
              {t("priced.panel.noBooks", "No active rate book was found, so no line can be priced. Load or publish a rate book first.")}
            </div>
          ) : (
            <div className="text-[12.5px] text-[var(--color-text-secondary)]">
              {t("priced.panel.books", "Rates from")}{" "}
              {view.rate_books.map((b, i) => (
                <span key={b.id}>
                  {i > 0 ? ", " : ""}
                  <span className="font-mono font-semibold">{b.code}</span> v{b.version}
                  {b.content_hash ? <span className="ml-1 font-mono text-[11px]">#{b.content_hash.slice(0, 8)}</span> : null}
                </span>
              ))}
            </div>
          )}

          {view.lines.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                    <th className="py-2 pr-3">{t("billing.col.item", "Item")}</th>
                    <th className="py-2 pr-3">{t("priced.col.description", "Description")}</th>
                    <th className="py-2 pr-3">{t("billing.col.floor", "Floor")}</th>
                    <th className="py-2 pr-3 text-right">{t("billing.col.qty", "Quantity")}</th>
                    <th className="py-2 pr-3 text-right">{t("priced.col.rate", "Rate")}</th>
                    <th className="py-2 pr-3 text-right">{t("priced.col.amount", "Amount")}</th>
                    <th className="py-2">{t("billing.col.basis", "Basis")}</th>
                  </tr>
                </thead>
                <tbody>
                  {view.lines.map((line, i) => (
                    <tr key={`${line.code}-${line.floor ?? ""}-${i}`} className="border-t border-[var(--color-border)] align-top">
                      <td className="py-2 pr-3 font-mono font-semibold">{line.code}</td>
                      <td className="py-2 pr-3">
                        {line.description ?? ""}
                        {line.spec ? <div className="text-[11.5px] text-[var(--color-text-muted)]">{`${line.spec.name.replace(/_/g, " ")} ${line.spec.value ?? "?"}`}</div> : null}
                        {line.unpriced_why ? <div className="text-[11.5px] text-[var(--color-danger)]">{line.unpriced_why}</div> : null}
                      </td>
                      <td className="py-2 pr-3">{line.floor ?? "—"}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {qty(line.qty)} {line.unit}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{line.rate === null ? "—" : `${money(line.rate)}${line.rate_unit ? ` / ${line.rate_unit}` : ""}`}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">{money(line.amount)}</td>
                      <td className="py-2">
                        {line.amount === null ? (
                          <Badge tone="red">{t("priced.unpriced", "Unpriced")}</Badge>
                        ) : (
                          <Badge tone={line.assumed_share > 0 ? "gold" : "green"}>{line.assumed_share > 0 ? t("billing.assumed", "Assumed") : t("billing.measured", "Measured")}</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title={t("billing.panel.noLines", "No quantity is billed yet")} description={t("billing.panel.noLinesBody", "No item of this project has a measured quantity.")} />
          )}

          {view.rate_notes.length > 0 ? (
            <ul className="space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
              {view.rate_notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : null}

          {view.materials.missing.length > 0 || view.materials.rows.length > 0 ? (
            <details>
              <summary className="cursor-pointer text-[13px] font-semibold">{t("priced.panel.materials", "Materials ({{n}} not counted)", { n: view.materials.missing.length })}</summary>
              <ul className="mt-2 space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {Object.entries(view.materials.totals).map(([m, v]) => (
                  <li key={m}>
                    <span className="font-semibold">{m.replace(/_/g, " ")}</span>: {qty(v)}
                  </li>
                ))}
                {view.materials.missing.map((m, i) => (
                  <li key={`${m.code}-${i}`}>
                    <span className="font-mono font-semibold">{m.code}</span>: {m.why}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      )}
    </Panel>
  );
}

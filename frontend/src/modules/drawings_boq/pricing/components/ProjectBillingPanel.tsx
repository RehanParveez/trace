import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, EmptyState, ErrorState, LoadingState, Panel, PanelHeader, StatCard } from "../../../organizations/components/OrganizationUi";
import { useBilling } from "../hooks/useBilling";
import type { BillLine } from "../types/billing.types";

interface ProjectBillingPanelProps {
  projectId: string;
}

const num = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: 3 }));

function specText(line: BillLine): string {
  return line.spec ? `${line.spec.name.replace(/_/g, " ")} ${line.spec.value ?? "?"}` : "";
}

export function ProjectBillingPanel({ projectId }: ProjectBillingPanelProps) {
  const { t } = useTranslation();
  const [profile, setProfile] = useState("PRIVATE_QS");
  const query = useBilling(projectId, profile);
  const view = query.data;

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("billing.panel.eyebrow", "BILLED QUANTITIES")}
        title={t("billing.panel.title", "Measured quantities, billed")}
        description={t(
          "billing.panel.desc",
          "The quantities measured for this project, grouped into bill lines under a billing method. Nothing here changes a measured quantity.",
        )}
        action={
          view ? (
            <select
              className="rounded-[8px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-[13px]"
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
              aria-label={t("billing.panel.profile", "Billing method")}
            >
              {view.profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          ) : null
        }
      />

      {query.isLoading ? (
        <LoadingState label={t("billing.panel.loading", "Loading billed quantities…")} />
      ) : query.isError || !view ? (
        <div className="p-5">
          <ErrorState title={t("billing.panel.loadError", "We couldn't load the billed quantities")} onRetry={() => void query.refetch()} />
        </div>
      ) : !view.has_ledger ? (
        <div className="p-5">
          <EmptyState
            title={t("billing.panel.noLedger", "No first-upload reading yet")}
            description={t("billing.panel.noLedgerBody", "Run the first-upload job on this project's drawings; the quantities are billed from what it reads and from the latest calculation run.")}
          />
        </div>
      ) : (
        <div className="space-y-5 p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label={t("billing.panel.statLines", "Bill lines")} value={view.lines.length} note={t("billing.panel.statLinesNote", "{{n}} measured entries", { n: view.counts.measured_entries })} icon="budget" tone="blue" />
            <StatCard
              label={t("billing.panel.statNeeded", "Rate needed")}
              value={view.rate_needed.length}
              note={t("billing.panel.statNeededNote", "No item in this billing method for them")}
              icon={view.rate_needed.length > 0 ? "alert" : "check"}
              tone={view.rate_needed.length > 0 ? "gold" : "green"}
            />
            <StatCard
              label={t("billing.panel.statNot", "Not measured")}
              value={view.counts.not_measured}
              note={t("billing.panel.statNotNote", "Asked or not read; not billed")}
              icon={view.counts.not_measured > 0 ? "alert" : "check"}
              tone={view.counts.not_measured > 0 ? "gold" : "green"}
            />
          </div>

          {!view.source.run ? (
            <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 text-[13px]">
              {t("billing.panel.noRun", "This project has no completed calculation run, so no quantity has been measured to bill.")}
            </div>
          ) : null}
          {view.source.no_family > 0 ? (
            <div className="text-[12.5px] text-[var(--color-text-secondary)]">
              {t("billing.panel.noFamily", "{{n}} measured rows name no bill line and are left out.", { n: view.source.no_family })}
            </div>
          ) : null}
          {!view.reconciled ? <Badge tone="red">{t("billing.panel.lost", "A measured quantity is not accounted for")}</Badge> : null}

          {view.lines.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                    <th className="py-2 pr-3">{t("billing.col.item", "Item")}</th>
                    <th className="py-2 pr-3">{t("billing.col.spec", "Specification")}</th>
                    <th className="py-2 pr-3">{t("billing.col.floor", "Floor")}</th>
                    <th className="py-2 pr-3 text-right">{t("billing.col.qty", "Quantity")}</th>
                    <th className="py-2 pr-3">{t("billing.col.unit", "Unit")}</th>
                    <th className="py-2">{t("billing.col.basis", "Basis")}</th>
                  </tr>
                </thead>
                <tbody>
                  {view.lines.map((line, i) => {
                    const assumed = line.sources.some((s) => s.assumed) || line.spec?.basis === "ASSUMED";
                    return (
                      <tr key={`${line.code}-${line.floor ?? ""}-${i}`} className="border-t border-[var(--color-border)]">
                        <td className="py-2 pr-3 font-mono font-semibold">{line.code}</td>
                        <td className="py-2 pr-3">{specText(line)}</td>
                        <td className="py-2 pr-3">{line.floor ?? "—"}</td>
                        <td className="py-2 pr-3 text-right tabular-nums">{num(line.qty)}</td>
                        <td className="py-2 pr-3">{line.unit}</td>
                        <td className="py-2">
                          <Badge tone={assumed ? "gold" : "green"}>{assumed ? t("billing.assumed", "Assumed") : t("billing.measured", "Measured")}</Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : view.source.run ? (
            <EmptyState title={t("billing.panel.noLines", "No quantity is billed yet")} description={t("billing.panel.noLinesBody", "No item of this project has a measured quantity.")} />
          ) : null}

          {view.included.length > 0 ? (
            <div className="text-[12.5px] text-[var(--color-text-secondary)]">
              {view.included.map((x) => (
                <div key={x.qty_key}>
                  {t("billing.panel.included", "{{qty}} {{unit}} of {{key}} is included in {{where}}", { qty: num(x.value), unit: x.unit, key: x.qty_key.replace(/_/g, " "), where: x.where })}
                </div>
              ))}
            </div>
          ) : null}

          {view.rate_needed.length > 0 ? (
            <details>
              <summary className="cursor-pointer text-[13px] font-semibold">{t("billing.panel.neededTitle", "Quantities with no item in this billing method ({{n}})", { n: view.rate_needed.length })}</summary>
              <ul className="mt-2 space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {view.rate_needed.map((r, i) => (
                  <li key={`${r.element}-${r.qty_key}-${i}`}>
                    <span className="font-mono font-semibold">{r.element}</span> {r.qty_key.replace(/_/g, " ")}: {num(r.value)} {r.unit}. {r.why}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {view.questions.length > 0 ? (
            <details>
              <summary className="cursor-pointer text-[13px] font-semibold">{t("billing.panel.questionsTitle", "Specifications still assumed ({{n}})", { n: view.questions.length })}</summary>
              <ul className="mt-2 space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {view.questions.map((q, i) => (
                  <li key={`${q.spec}-${q.floor ?? ""}-${i}`}>
                    {q.question} {t("billing.panel.default", "Using {{value}} until answered.", { value: q.default ?? "—" })}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {view.not_measured.length > 0 ? (
            <details>
              <summary className="cursor-pointer text-[13px] font-semibold">{t("billing.panel.notTitle", "Items not billed because they are not measured ({{n}})", { n: view.not_measured.length })}</summary>
              <ul className="mt-2 space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {view.not_measured.map((n, i) => (
                  <li key={`${n.element}-${n.floor ?? ""}-${i}`}>
                    <span className="font-mono font-semibold">{n.element}</span> {n.name ?? ""}
                    {n.floor ? ` · ${n.floor}` : ""} · {n.state}
                    {n.reasons.length > 0 ? ` · ${n.reasons.join(", ")}` : ""}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {view.unavailable.length > 0 ? (
            <details>
              <summary className="cursor-pointer text-[13px] font-semibold">{t("billing.panel.unavailTitle", "Other quantities of these items are not available ({{n}})", { n: view.unavailable.length })}</summary>
              <ul className="mt-2 space-y-1 text-[12.5px] text-[var(--color-text-secondary)]">
                {view.unavailable.map((u) => (
                  <li key={`${u.element}-${u.qty}`}>
                    <span className="font-mono font-semibold">{u.element}</span> {u.qty.replace(/_/g, " ")} ({u.unit}): {u.why}
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

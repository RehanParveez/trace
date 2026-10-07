import { useTranslation } from "react-i18next";
import { Badge, Panel, PanelHeader, TableShell } from "../../../organizations/components/OrganizationUi";
import { useRebarSummary } from "../hooks/useRebar";
import { formatPrecise } from "../../utils/drawings-boq.utils";

const th = "px-4 py-3 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]";

export function RebarSummaryPanel({ versionId }: { versionId: string }) {
  const { t } = useTranslation();
  const query = useRebarSummary(versionId);
  const s = query.data;
  if (query.isLoading || query.isError || !s || Number(s.total_kg) === 0) return null;

  const tiles: [string, string, string?][] = [
    [t("rebar.summary.total", "Total steel"), `${formatPrecise(s.total_kg, 2)} kg`],
    [t("rebar.summary.model", "From model"), `${formatPrecise(s.tier1_kg, 2)} kg`],
    [t("rebar.summary.schedule", "From bar schedule"), `${formatPrecise(s.tier2_kg, 2)} kg`],
    [t("rebar.summary.estimate", "Estimated"), `${formatPrecise(s.tier3_estimate_kg, 2)} kg`, Number(s.tier3_estimate_kg) > 0 ? "text-[var(--color-warning)]" : ""],
  ];

  return (
    <Panel>
      <PanelHeader
        eyebrow={t("rebar.eyebrow", "Reinforcement")}
        title={t("rebar.summary.title", "Steel by diameter")}
        description={t("rebar.summary.description", "Bar marks behind the steel lines of this BOQ. Estimated steel is never part of the bar bending schedule export.")}
        action={s.bbs_exportable
          ? <Badge tone="green">{t("rebar.summary.bbsReady", "BBS export ready")}</Badge>
          : <Badge tone="gold">{Number(s.tier3_estimate_kg) > 0 ? t("rebar.summary.hasEstimate", "Includes estimated steel") : t("rebar.summary.noBbs", "No scheduled steel")}</Badge>}
      />
      <div className="grid grid-cols-2 gap-3 border-b border-[var(--color-border)] p-5 sm:grid-cols-4">
        {tiles.map(([k, v, c]) => (
          <div key={k}>
            <div className={`font-mono text-[15px] font-semibold ${c ?? ""}`}>{v}</div>
            <div className="text-[11px] text-[var(--color-text-muted)]">{k}</div>
          </div>
        ))}
      </div>
      <TableShell>
        <table className="w-full min-w-[560px] text-left">
          <thead className="bg-[var(--color-surface-muted)]"><tr>
            <th className={th}>{t("rebar.colDia", "Dia mm")}</th>
            <th className={th}>{t("rebar.summary.size", "Size")}</th>
            <th className={th}>{t("rebar.grade", "grade")}</th>
            <th className={`${th} text-right`}>{t("rebar.summary.marks", "Bar marks")}</th>
            <th className={`${th} text-right`}>{t("rebar.summary.length", "Length m")}</th>
            <th className={`${th} text-right`}>kg</th>
          </tr></thead>
          <tbody>
            {s.rows.map((r) => (
              <tr key={`${r.dia_mm}-${r.designation}-${r.grade}`} className="border-t border-[var(--color-border)]">
                <td className="px-4 py-3 font-mono text-[12.5px]">{formatPrecise(r.dia_mm, 3)}</td>
                <td className="px-4 py-3 text-[12.5px]">{r.designation ?? "—"}</td>
                <td className="px-4 py-3 text-[12.5px]">{r.grade ?? "—"}</td>
                <td className="px-4 py-3 text-right font-mono text-[12.5px]">{r.mark_count}</td>
                <td className="px-4 py-3 text-right font-mono text-[12.5px]">{formatPrecise(r.total_len_m, 2)}</td>
                <td className="px-4 py-3 text-right font-mono text-[12.5px] font-semibold">{formatPrecise(r.total_kg, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableShell>
    </Panel>
  );
}

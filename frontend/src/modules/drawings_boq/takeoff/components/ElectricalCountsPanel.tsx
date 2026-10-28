import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../organizations/components/OrganizationUi";
import type { TakeoffCandidate } from "../types/takeoff.types";

interface Props {
  candidates: TakeoffCandidate[];
  onShow: (c: TakeoffCandidate) => void;
}

interface CountRow {
  c: TakeoffCandidate;
  symbol: string;
  group: string;
  count: number;
  legendRow: number | null;
  legendPage: number | null;
  ocr: boolean;
  fromStructure: boolean;
}

const GROUP_ORDER = ["ELEC_LIGHT", "ELEC_FAN", "ELEC_SOCKET", "ELEC_SWITCH", "ELEC_LOWV", "ELEC_BOARD", "ELEC_OTHER"];
const GROUP_TEXT: Record<string, string> = {
  ELEC_LIGHT: "Lights",
  ELEC_FAN: "Fans",
  ELEC_SOCKET: "Sockets and plugs",
  ELEC_SWITCH: "Switches",
  ELEC_LOWV: "Telephone, TV, data, alarm and bell points",
  ELEC_BOARD: "Boards, earthing and supply",
  ELEC_OTHER: "Other electrical points",
};

function rowOf(c: TakeoffCandidate): { floor: string | null; row: CountRow } | null {
  const f = (c.facts ?? {}) as Record<string, unknown>;
  if (typeof f.electrical !== "string") return null;
  return {
    floor: typeof f.electrical_floor === "string" && f.electrical_floor ? f.electrical_floor : null,
    row: {
      c,
      symbol: f.electrical,
      group: typeof f.electrical_group === "string" ? f.electrical_group : "ELEC_OTHER",
      count: c.count,
      legendRow: typeof f.legend_row === "number" ? f.legend_row : null,
      legendPage: typeof f.legend_page === "number" ? f.legend_page : null,
      ocr: f.legend_ocr === true,
      fromStructure: f.legend_source === "STRUCTURE",
    },
  };
}

export function ElectricalCountsPanel({ candidates, onShow }: Props) {
  const { t } = useTranslation();
  const floors = useMemo(() => {
    const by = new Map<string, CountRow[]>();
    for (const c of candidates) {
      const r = rowOf(c);
      if (!r) continue;
      const key = r.floor ?? "";
      by.set(key, [...(by.get(key) ?? []), r.row]);
    }
    return [...by.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [candidates]);
  if (floors.length === 0) return null;
  return (
    <section className="space-y-3 rounded-[10px] border border-[var(--color-border)] p-3" data-testid="electrical-counts">
      <h3 className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.electrical.title", "Electrical points counted on this sheet")}</h3>
      {floors.map(([floor, rows]) => {
        const sorted = [...rows].sort((a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group) || a.symbol.localeCompare(b.symbol));
        const total = sorted.reduce((n, r) => n + r.count, 0);
        return (
          <div key={floor || "none"} data-testid="electrical-floor">
            <div className="mb-1 flex items-center gap-2 text-[13px] font-semibold">
              <span>{floor ? floor.charAt(0) + floor.slice(1).toLowerCase() : t("boq.takeoff.electrical.noFloor", "Floor not known")}</span>
              <span className="ml-auto font-mono text-[12px] text-[var(--color-text-secondary)]">{total}</span>
            </div>
            <table className="w-full text-left text-[12.5px]">
              <thead>
                <tr className="text-[11px] uppercase text-[var(--color-text-muted)]">
                  <th className="py-1 pr-2">{t("boq.takeoff.electrical.item", "Item")}</th>
                  <th className="py-1 pr-2">{t("boq.takeoff.electrical.symbol", "Symbol")}</th>
                  <th className="py-1 pr-2 text-right">{t("boq.takeoff.electrical.count", "Count")}</th>
                  <th className="py-1 pr-2">{t("boq.takeoff.electrical.legend", "Legend row")}</th>
                  <th className="py-1" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.c.id} className="border-t border-[var(--color-border)]" data-testid="electrical-row">
                    <td className="py-1 pr-2">{GROUP_TEXT[r.group] ?? r.group}</td>
                    <td className="py-1 pr-2">{r.symbol}</td>
                    <td className="py-1 pr-2 text-right font-mono">{r.count}</td>
                    <td className="py-1 pr-2">
                      {r.legendRow !== null ? (
                        <span className="font-mono">{r.legendRow + 1}{r.legendPage !== null ? ` · ${t("boq.takeoff.electrical.page", "page")} ${r.legendPage}` : ""}</span>
                      ) : (
                        <span className="text-[var(--color-text-muted)]">–</span>
                      )}
                      {r.fromStructure ? <Badge tone="slate">{t("boq.takeoff.electrical.byStructure", "no table")}</Badge> : null}
                      {r.ocr ? <Badge tone="gold">{t("boq.takeoff.electrical.ocr", "read by OCR")}</Badge> : null}
                    </td>
                    <td className="py-1 text-right">
                      <Button size="sm" variant="ghost" onClick={() => onShow(r.c)}>{t("boq.takeoff.counts.show", "Show")}</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </section>
  );
}

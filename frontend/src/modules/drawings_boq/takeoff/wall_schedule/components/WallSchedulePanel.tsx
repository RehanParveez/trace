import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, Button } from "../../../../organizations/components/OrganizationUi";
import { floorName } from "../../utils/floorSources";
import { wallScheduleApi } from "../api/wallSchedule.api";
import { useWallSchedule } from "../hooks/useWallSchedule";
import type { FloorCompare, WallItem } from "../types/wallSchedule.types";

interface Props {
  drawingId: string;
}

const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";
const CELL = "border-b border-[var(--color-border)] px-2 py-1 align-top";

function inches(mm: number): string {
  return `${Math.round((mm / 25.4) * 10) / 10}"`;
}

function compareText(v: FloorCompare): string {
  if (v === "ONLY_THIS_FLOOR") return "only here";
  if (v === "COVERED") return "same as";
  if (v === "NO_COMMON_FRAME") return "not comparable";
  return "\u2014";
}

function itemText(i: WallItem): string {
  return i.quantity === null ? i.item : `${i.item} ${i.quantity} ${i.unit ?? ""}`.trim();
}

export function WallSchedulePanel({ drawingId }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const report = useWallSchedule(drawingId, open);
  const rows = report.data?.rows ?? [];
  const floors = report.data?.floors ?? [];

  async function download() {
    setBusy(true);
    try {
      const blob = await wallScheduleApi.xlsx(drawingId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "wall-schedule.xlsx";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => window.URL.revokeObjectURL(url), 30000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="wall-schedule" onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}>
      <summary className="flex cursor-pointer flex-wrap items-center gap-2">
        <span className="font-semibold">{t("boq.takeoff.wallSchedule.title", "Wall schedule")}</span>
        {report.data ? <Badge tone="slate">{t("boq.takeoff.wallSchedule.count", "{{n}} wall runs", { n: rows.length })}</Badge> : null}
      </summary>
      <p className={`mt-2 ${MUTED}`}>
        {t("boq.takeoff.wallSchedule.help", "Each wall run of each floor, named by the spaces on its two faces, with its thickness, length, height and the items worked out from it. A run marked only here has no run of the floor next to it within the tolerance shown. Nothing on this list changes a quantity.")}
      </p>
      {report.isLoading ? <p className={MUTED}>{t("boq.takeoff.wallSchedule.loading", "Reading the wall runs\u2026")}</p> : null}
      {report.isError ? <p className="text-[var(--color-danger,#b42318)]">{t("boq.takeoff.wallSchedule.failed", "The wall schedule could not be loaded.")}</p> : null}
      {floors.length > 0 ? (
        <div className="mt-2" data-testid="wall-schedule-floors">
          <table className="w-full text-left">
            <thead>
              <tr className={MUTED}>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.floor", "Floor")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.runs", "Runs")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.length", "Length (m)")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.byThickness", "By thickness")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.onlyBelow", "Only here, against the floor below")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.onlyAbove", "Only here, against the floor above")}</th>
              </tr>
            </thead>
            <tbody>
              {floors.map((f) => (
                <tr key={f.floor}>
                  <td className={CELL}>{floorName(f.floor)}</td>
                  <td className={CELL}>{f.runs}</td>
                  <td className={CELL}>{f.length_m}</td>
                  <td className={CELL}>{Object.entries(f.by_thickness_mm).map(([mm, m]) => `${inches(Number(mm))}: ${m} m`).join(" \u00b7 ")}</td>
                  <td className={CELL}>{f.only_vs_below}</td>
                  <td className={CELL}>{f.only_vs_above}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {rows.length > 0 ? (
        <div className="mt-2 overflow-x-auto" data-testid="wall-schedule-rows">
          <div className="mb-1 flex items-center gap-2">
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => void download()}>{t("boq.takeoff.wallSchedule.download", "Download as Excel")}</Button>
          </div>
          <table className="w-full text-left">
            <thead>
              <tr className={MUTED}>
                <th className={CELL}>#</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.floor", "Floor")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.wall", "Wall")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.thickness", "Thickness")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.length", "Length (m)")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.height", "Height (mm)")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.items", "Items")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.below", "Floor below")}</th>
                <th className={CELL}>{t("boq.takeoff.wallSchedule.above", "Floor above")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-testid={`wall-run-${r.no}`}>
                  <td className={CELL}>{r.no}</td>
                  <td className={CELL}>{r.floor ? floorName(r.floor) : "\u2014"}</td>
                  <td className={CELL}>{r.name}</td>
                  <td className={CELL}>{inches(r.thickness_mm)} <span className={MUTED}>{r.thickness_basis.toLowerCase()}</span></td>
                  <td className={CELL}>{r.length_m}</td>
                  <td className={CELL}>{r.height_mm ?? "\u2014"}</td>
                  <td className={CELL}>{r.items.map(itemText).join("; ")}</td>
                  <td className={CELL}>{compareText(r.vs_below)}</td>
                  <td className={CELL}>{compareText(r.vs_above)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </details>
  );
}

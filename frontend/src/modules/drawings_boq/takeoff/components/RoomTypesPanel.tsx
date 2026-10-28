import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Badge, inputClass, useToast } from "../../../organizations/components/OrganizationUi";
import { useProjectFinishRules, useSaveProjectFinishRules } from "../hooks/useFinishRules";
import { ROOM_TYPES, roomTypeText } from "../types/finishRules.types";
import type { TakeoffCandidate } from "../types/takeoff.types";
import { takeoffErrorMessage } from "../utils/errors";

interface Props {
  candidates: TakeoffCandidate[];
  projectId?: string;
  canEdit: boolean;
}

interface Row {
  name: string;
  type: string;
  rooms: number;
  area: number;
}

const ROOM_KEY = "finish.room_type";

export function RoomTypesPanel({ candidates, projectId, canEdit }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const rules = useProjectFinishRules(projectId);
  const save = useSaveProjectFinishRules(projectId);
  const mine = useMemo(() => {
    const out = new Map<string, string>();
    for (const r of rules.data?.rules ?? []) {
      if (r.key === ROOM_KEY && typeof r.value === "string" && r.scope.room_name) out.set(r.scope.room_name, r.value);
    }
    return out;
  }, [rules.data]);
  const rows = useMemo(() => {
    const by = new Map<string, Row>();
    for (const c of candidates) {
      if (c.category !== "ROOM") continue;
      const f = (c.facts ?? {}) as Record<string, unknown>;
      const name = typeof f.name === "string" && f.name.trim() ? f.name.trim().toUpperCase() : "";
      if (!name) continue;
      const area = typeof f.area_m2 === "number" ? f.area_m2 : 0;
      const prev = by.get(name);
      by.set(name, { name, type: typeof f.room_type === "string" ? f.room_type : "OTHER", rooms: (prev?.rooms ?? 0) + 1, area: (prev?.area ?? 0) + area });
    }
    return [...by.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [candidates]);
  if (rows.length === 0) return null;
  const set = (name: string, type: string) => {
    save.mutate(
      { rules: [{ key: ROOM_KEY, scope: { room_name: name }, value: type || null }] },
      {
        onSuccess: () => showToast({ tone: "success", title: t("boq.takeoff.roomTypes.saved", "Room type saved for this project. Read the sheet again to apply it.") }),
        onError: (e) => showToast({ tone: "error", title: t("boq.takeoff.roomTypes.saveFailed", "Could not save"), description: takeoffErrorMessage(e) }),
      },
    );
  };
  return (
    <section className="space-y-2 rounded-[10px] border border-[var(--color-border)] p-3" data-testid="room-types">
      <h3 className="text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.roomTypes.title", "Room types")}</h3>
      <p className="text-[12px] text-[var(--color-text-muted)]">
        {t("boq.takeoff.roomTypes.note", "The type of a room decides its finishes: baths, toilets and powder rooms are wet rooms; the porch, terrace, passage and lawn can have a floor item of their own; a look-below, a void and a double height have no floor.")}
      </p>
      <table className="w-full text-left text-[12.5px]">
        <thead>
          <tr className="text-[11px] uppercase text-[var(--color-text-muted)]">
            <th className="py-1 pr-2">{t("boq.takeoff.roomTypes.room", "Room")}</th>
            <th className="py-1 pr-2 text-right">{t("boq.takeoff.roomTypes.area", "m²")}</th>
            <th className="py-1">{t("boq.takeoff.roomTypes.type", "Type")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const own = mine.get(r.name);
            return (
              <tr key={r.name} className="border-t border-[var(--color-border)]" data-testid="room-type-row">
                <td className="py-1 pr-2">{r.name}{r.rooms > 1 ? ` × ${r.rooms}` : ""}</td>
                <td className="py-1 pr-2 text-right font-mono">{r.area.toFixed(2)}</td>
                <td className="py-1">
                  {canEdit && projectId ? (
                    <select className={inputClass} value={own ?? r.type} disabled={save.isPending} onChange={(e) => set(r.name, e.target.value === r.type && !own ? "" : e.target.value)}>
                      {ROOM_TYPES.map((x) => <option key={x} value={x}>{roomTypeText(x)}</option>)}
                    </select>
                  ) : (
                    <span>{roomTypeText(own ?? r.type)}</span>
                  )}
                  {own ? <Badge tone="gold">{t("boq.takeoff.roomTypes.yours", "set for this project")}</Badge> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

import { useTranslation } from "react-i18next";
import { Badge, Button, EmptyState } from "../../../organizations/components/OrganizationUi";
import type { ShapeList, TagSummary, TakeoffMeasurement } from "../types/takeoff.types";
import { tagTally } from "../utils/tagTally";

interface Props {
  tags: TagSummary[] | undefined;
  shapes: ShapeList | undefined;
  measurements: TakeoffMeasurement[];
  canEdit: boolean;
  blocked: string | null;
  busy: boolean;
  onPreviewTag: (tag: string) => void;
  onUseTag: (tag: string) => void;
  onPreviewShape: (id: string) => void;
  onUseShape: (id: string) => void;
  onClear: () => void;
}

export function CountsPanel(p: Props) {
  const { t } = useTranslation();
  const tags = p.tags ?? [];
  const shapes = p.shapes?.shapes ?? [];
  if (tags.length === 0 && shapes.length === 0) {
    return <EmptyState icon="info" title={t("boq.takeoff.counts.emptyTitle", "No tags or repeated shapes found")} description={t("boq.takeoff.counts.emptyDesc", "Counts are suggested from tags such as C1 or B2 and from identical shapes. You can still count by clicking.")} />;
  }
  return (
    <div className="space-y-5 p-4" data-testid="counts-panel">
      {p.blocked ? <div className="rounded-[8px] bg-[var(--color-warning-bg)] p-2.5 text-[12.5px]">{p.blocked}</div> : null}
      {tags.length > 0 ? (
        <section>
          <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.counts.tags", "Tags on this sheet")}</h3>
          <ul className="space-y-2">
            {tags.map((tg) => {
              const tally = tagTally(p.measurements, tg.tag);
              const counted = tally.confirmed + tally.draft;
              const ok = counted === tg.in_drawing;
              return (
                <li key={tg.tag} className="rounded-[8px] border border-[var(--color-border)] p-2.5" data-testid="tag-row">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[14px] font-semibold">{tg.tag}</span>
                    <span className="text-[12.5px] text-[var(--color-text-secondary)]">× {tg.in_drawing} {t("boq.takeoff.counts.found", "found")}</span>
                    <span className="ml-auto">
                      {counted === 0 ? <Badge tone="slate">{t("boq.takeoff.counts.notCounted", "not counted")}</Badge> : ok ? <Badge tone="green">{t("boq.takeoff.counts.allCounted", "all counted")} ✓</Badge> : <Badge tone="red">{t("boq.takeoff.counts.counted", "counted")} {counted} / {tg.in_drawing}</Badge>}
                    </span>
                  </div>
                  {counted > 0 ? <div className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{tally.confirmed} {t("boq.takeoff.list.confirmed", "Confirmed").toLowerCase()} · {tally.draft} {t("boq.takeoff.list.drafts", "Drafts").toLowerCase()}</div> : null}
                  <div className="mt-1.5 flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => p.onPreviewTag(tg.tag)}>{t("boq.takeoff.counts.show", "Show")}</Button>
                    {p.canEdit ? <Button size="sm" disabled={p.busy || Boolean(p.blocked)} onClick={() => p.onUseTag(tg.tag)} data-testid="use-tag">{t("boq.takeoff.counts.countAll", "Count all")} {tg.tag}</Button> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
      {shapes.length > 0 ? (
        <section>
          <h3 className="mb-2 text-[11px] font-bold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">{t("boq.takeoff.counts.shapes", "Repeated shapes")}</h3>
          <ul className="space-y-2">
            {shapes.map((s) => (
              <li key={s.id} className="rounded-[8px] border border-[var(--color-border)] p-2.5" data-testid="shape-row">
                <div className="flex items-center gap-2 text-[13px]">
                  <span className="font-semibold">{s.shape}</span>
                  <span className="font-mono text-[12px] text-[var(--color-text-secondary)]">{s.a_mm !== null && s.b_mm !== null ? `${Math.round(s.a_mm)} × ${Math.round(s.b_mm)} mm` : `${s.a_pt.toFixed(1)} × ${s.b_pt.toFixed(1)} pt`}</span>
                  <span className="ml-auto text-[12.5px]">× {s.count}</span>
                </div>
                <div className="mt-1.5 flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => p.onPreviewShape(s.id)}>{t("boq.takeoff.counts.show", "Show")}</Button>
                  {p.canEdit ? <Button size="sm" disabled={p.busy || Boolean(p.blocked)} onClick={() => p.onUseShape(s.id)}>{t("boq.takeoff.counts.countShape", "Count these")}</Button> : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <Button size="sm" variant="ghost" onClick={p.onClear}>{t("boq.takeoff.counts.clearMarks", "Clear marks")}</Button>
    </div>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, useToast } from "../../../../organizations/components/OrganizationUi";
import { useGrades, useStampGrades, useUnstampGrades } from "../hooks/useGrades";
import { takeoffErrorMessage } from "../../utils/errors";
import { canStamp, canUnstamp, changedText, concreteText, confirmedNote, conflictText, isEmpty, memberStatus, noteSource, ourConflicts, plasterText, soilText, steelText, summaryLine } from "../utils/grades";

interface Props {
  drawingId: string;
  canEdit: boolean;
}

const BTN = "rounded-[8px] border border-[var(--color-border)] px-2 py-0.5 text-[11.5px] disabled:opacity-50";
const MUTED = "text-[11.5px] text-[var(--color-text-secondary)]";

export function PrintedGradesPanel({ drawingId, canEdit }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const report = useGrades(drawingId);
  const stamp = useStampGrades(drawingId);
  const unstamp = useUnstampGrades(drawingId);
  const [includeConfirmed, setIncludeConfirmed] = useState(false);
  const data = report.data;
  if (report.isLoading || (report.isError && !data)) return null;
  if (!data || isEmpty(data)) return null;
  const busy = stamp.isPending || unstamp.isPending;
  const fail = (title: string) => (e: unknown) => showToast({ tone: "error", title, description: takeoffErrorMessage(e) });
  const line = summaryLine(data);
  const plaster = plasterText(data.plaster);
  const soil = soilText(data.soil);
  const conflicts = ourConflicts(data);
  const members = data.members.filter((m) => m.concrete || m.steel || m.concrete_clash.length || m.steel_clash.length);
  const confirmed = confirmedNote(data);
  return (
    <details className="border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="printed-grades">
      <summary className="cursor-pointer">
        <span className="font-semibold">{t("boq.takeoff.grades.title", "Grades and notes printed on the drawing")}</span>
        {line ? <span className={`ml-2 ${MUTED}`}>{line}</span> : null}
      </summary>
      <div className="mt-2 space-y-3">
        <p className={MUTED}>{t("boq.takeoff.grades.hint", "A grade is given to a member only when the drawing prints exactly one for that kind of member. Two different ones give none, and nothing is guessed.")}</p>

        {members.length ? (
          <table className="w-full text-[12px]" data-testid="printed-grades-members">
            <thead>
              <tr className="text-left text-[var(--color-text-muted)]">
                <th className="font-medium">{t("boq.takeoff.grades.member", "Member")}</th>
                <th className="font-medium">{t("boq.takeoff.grades.concrete", "Concrete")}</th>
                <th className="font-medium">{t("boq.takeoff.grades.steel", "Steel")}</th>
                <th className="font-medium">{t("boq.takeoff.grades.measured", "Measured")}</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.member} className="align-top" data-testid={`printed-grades-member-${m.member}`}>
                  <td className="font-semibold">{m.label}</td>
                  <td>{m.concrete_clash.length ? <Badge tone="gold">{concreteText(m)}</Badge> : concreteText(m) || "-"}</td>
                  <td>{m.steel_clash.length ? <Badge tone="gold">{steelText(m)}</Badge> : steelText(m) || "-"}</td>
                  <td className={MUTED} title={noteSource(m) || undefined}>{memberStatus(m)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}

        {canEdit && (canStamp(data) || canUnstamp(data)) ? (
          <div className="space-y-1" data-testid="printed-grades-actions">
            <div className="flex flex-wrap items-center gap-2">
              {canStamp(data) ? (
                <button type="button" className={BTN} disabled={busy} data-testid="printed-grades-stamp"
                  onClick={() => stamp.mutate({ include_confirmed: includeConfirmed }, {
                    onSuccess: (r) => showToast({ tone: "success", title: changedText(r.changed, "stamp") }),
                    onError: fail(t("boq.takeoff.grades.stampError", "Could not give the printed mix")),
                  })}>
                  {t("boq.takeoff.grades.stamp", "Give the printed mix to the {{n}} measured members", { n: data.summary.open ?? 0 })}
                </button>
              ) : null}
              {canUnstamp(data) ? (
                <button type="button" className={BTN} disabled={busy} data-testid="printed-grades-unstamp"
                  onClick={() => unstamp.mutate(undefined, {
                    onSuccess: (r) => showToast({ tone: "success", title: changedText(r.changed, "unstamp") }),
                    onError: fail(t("boq.takeoff.grades.unstampError", "Could not take the printed mix back")),
                  })}>
                  {t("boq.takeoff.grades.unstamp", "Take the printed mix back")}
                </button>
              ) : null}
            </div>
            {confirmed && canStamp(data) ? (
              <label className={`flex items-center gap-1.5 ${MUTED}`}>
                <input type="checkbox" checked={includeConfirmed} onChange={(e) => setIncludeConfirmed(e.target.checked)} data-testid="printed-grades-include-confirmed" />
                <span>{confirmed}</span>
              </label>
            ) : null}
            <p className={MUTED}>{t("boq.takeoff.grades.stampHint", "A grade you typed yourself is never replaced. Items you accept from now on take the printed mix as they are accepted.")}</p>
          </div>
        ) : null}

        {plaster ? (
          <section data-testid="printed-grades-plaster">
            <p className="font-semibold">{t("boq.takeoff.grades.plaster", "Plaster")}</p>
            <p className={MUTED}>{plaster}</p>
          </section>
        ) : null}

        {soil.length ? (
          <section data-testid="printed-grades-soil">
            <p className="font-semibold">{t("boq.takeoff.grades.soil", "Soil stabilisation")}</p>
            {soil.map((s) => <p key={s} className={MUTED}>{s}</p>)}
          </section>
        ) : null}

        {conflicts.length ? (
          <section data-testid="printed-grades-conflicts">
            {conflicts.map((c, i) => <p key={`${c.param}-${i}`} className={MUTED}>{conflictText(c)}</p>)}
          </section>
        ) : null}
      </div>
    </details>
  );
}

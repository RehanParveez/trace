import { useTranslation } from "react-i18next";
import { Button } from "../../../organizations/components/OrganizationUi";
import type { CandidateFailure } from "../types/takeoff.types";

interface Props {
  failures: CandidateFailure[];
  canEdit: boolean;
  busy: boolean;
  onAcceptAnyway: (ids: string[]) => void;
  onReject: (ids: string[]) => void;
  onDismiss: () => void;
}

export function RepeatMarksNotice({ failures, canEdit, busy, onAcceptAnyway, onReject, onDismiss }: Props) {
  const { t } = useTranslation();
  if (failures.length === 0) return null;
  const ids = failures.map((f) => f.id);
  return (
    <section className="space-y-1 border-b border-[var(--color-border)] bg-[var(--color-warning-bg)] p-3 text-[12px]" data-testid="repeat-marks" data-count={failures.length}>
      <div className="font-semibold text-[var(--color-warning)]">
        {t("boq.takeoff.repeat.title", "{{n}} not added: the mark is already accepted from another sheet", { n: failures.length })}
      </div>
      <ul className="list-none space-y-0.5 pl-0 text-[var(--color-text-secondary)]">
        {failures.slice(0, 5).map((f) => <li key={f.id} data-testid="repeat-mark-line">{f.message}</li>)}
        {failures.length > 5 ? <li>{t("boq.takeoff.repeat.more", "and {{n}} more", { n: failures.length - 5 })}</li> : null}
      </ul>
      <div className="flex flex-wrap gap-2 pt-1">
        <Button size="sm" variant="secondary" disabled={!canEdit || busy} onClick={() => onReject(ids)} data-testid="repeat-reject">
          {t("boq.takeoff.repeat.reject", "Reject these repeats")}
        </Button>
        <Button size="sm" variant="ghost" disabled={!canEdit || busy} onClick={() => onAcceptAnyway(ids)} data-testid="repeat-accept-anyway">
          {t("boq.takeoff.repeat.acceptAnyway", "Accept them anyway")}
        </Button>
        <Button size="sm" variant="ghost" onClick={onDismiss} data-testid="repeat-dismiss">{t("boq.takeoff.repeat.dismiss", "Leave them")}</Button>
      </div>
    </section>
  );
}

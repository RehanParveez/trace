import { useTranslation } from "react-i18next";
import { Button } from "../../../organizations/components/OrganizationUi";
import type { ReadyToAccept } from "../types/takeoff.types";
import { heldLine, heldOnSheet, readyOnSheet } from "../utils/ready";

interface Props {
  data: ReadyToAccept | undefined;
  pageNo: number;
  canEdit: boolean;
  busy: boolean;
  onAccept: (ids: string[]) => void;
}

export function ReadyToAcceptPanel(p: Props) {
  const { t } = useTranslation();
  if (!p.data) return null;
  const ready = readyOnSheet(p.data, p.pageNo);
  const held = heldOnSheet(p.data, p.pageNo);
  if (ready.length === 0 && held.length === 0) return null;
  return (
    <section className="space-y-1 border-b border-[var(--color-border)] p-3 text-[12px]" data-testid="ready-to-accept" data-ready={ready.length}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t("boq.takeoff.ready.title", "Pass every check")}</h3>
        <span className="text-[var(--color-text-secondary)]" data-testid="ready-count">
          {t("boq.takeoff.ready.count", "{{n}} on this sheet", { n: ready.length })}
        </span>
        <Button
          type="button"
          variant="secondary"
          data-testid="ready-accept"
          disabled={!p.canEdit || p.busy || ready.length === 0}
          onClick={() => p.onAccept(ready.map((r) => r.id))}
        >
          {t("boq.takeoff.ready.accept", "Accept these {{n}}", { n: ready.length })}
        </Button>
      </div>
      {ready.length > 0 ? (
        <details className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="ready-basis">
          <summary className="cursor-pointer">{t("boq.takeoff.ready.basis", "Why these are safe")}</summary>
          <ul className="mt-1 space-y-0.5">
            {ready.map((r) => (
              <li key={r.id}>
                <span className="font-semibold">{r.tag ?? r.category}</span>
                {r.floor ? ` \u00b7 ${r.floor}` : ""}
                {` \u00b7 ${r.safe_basis?.text ?? ""}`}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {held.length > 0 ? (
        <p className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="ready-held">
          {t("boq.takeoff.ready.held", "{{n}} need a look first: {{why}}.", { n: held.length, why: heldLine(held) })}
        </p>
      ) : null}
    </section>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../organizations/components/OrganizationUi";
import type { PdfReadability } from "../types/takeoff.types";
import { READABILITY_TEXT, READABILITY_TONE, pagesLabel, reasonTitle, shownState } from "../utils/readability";

interface Props {
  value: PdfReadability | null | undefined;
}

export function ReadabilityChip({ value }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const state = shownState(value);
  if (!value || !state) return null;
  const reasons = value.reasons ?? [];
  return (
    <div className="text-[11.5px] text-[var(--color-text-secondary)]" data-testid="readability" data-state={state}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={READABILITY_TONE[state]}>{t(`takeoff.readability.state.${state}`, READABILITY_TEXT[state])}</Badge>
        {reasons.length ? (
          <button type="button" className="underline" onClick={() => setOpen((v) => !v)} data-testid="readability-toggle">
            {open ? t("takeoff.readability.hide", "Hide why") : t("takeoff.readability.show", "Why?")}
          </button>
        ) : null}
      </div>
      {open && reasons.length ? (
        <ul className="mt-1 list-none space-y-1 pl-0" data-testid="readability-reasons">
          {reasons.map((r) => (
            <li key={r.code} data-testid={`readability-${r.code}`}>
              <span className="font-semibold">{t(`takeoff.readability.reason.${r.code}`, reasonTitle(r))}</span>
              <span className="text-[var(--color-text-muted)]"> · {pagesLabel(r.pages, r.sheets)}</span>
              <span className="block text-[var(--color-text-muted)]">{r.text}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

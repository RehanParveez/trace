import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Icon } from "../../../organizations/components/OrganizationUi";
import { IDENTITY_PERMISSIONS, usePermissionKeys } from "../../../identity";
import type { WaitingPdf } from "../utils/runDrawings";
import { ApprovePdfDialog } from "./ApprovePdfDialog";
import { ReadabilityChip } from "./ReadabilityChip";

interface PdfRunReadinessProps {
  projectId: string;
  waiting: WaitingPdf[];
}

export function PdfRunReadiness({ projectId, waiting }: PdfRunReadinessProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const canApprove = usePermissionKeys().includes(IDENTITY_PERMISSIONS.BOQ_UPDATE);
  const [open, setOpen] = useState<WaitingPdf | null>(null);
  if (waiting.length === 0) return null;
  return (
    <div className="md:col-span-2" data-testid="pdf-waiting">
      <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
        {t("takeoff.runReady.title", "PDF drawings waiting for approval")}
      </span>
      <p className="mt-1 text-[11.5px] text-[var(--color-text-secondary)]">
        {t("takeoff.runReady.hint", "A PDF is calculated from its confirmed measurements. These have none yet, so they cannot be selected above.")}
      </p>
      <ul className="mt-1.5 divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
        {waiting.map(({ drawing, row }) => (
          <li key={drawing.id} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[12.5px] font-semibold text-[var(--color-text-primary)]">{drawing.original_filename}</span>
              <span className="block text-[11px] text-[var(--color-text-muted)]">
                {t("takeoff.runReady.counts", { defaultValue: "{{sheets}} sheets · {{draft}} draft measurements · 0 confirmed", sheets: row.sheets, draft: row.draft })}
              </span>
            </span>
            <Badge tone="gold">PDF</Badge>
            {canApprove ? (
              <Button variant="primary" size="sm" onClick={() => setOpen({ drawing, row })}>
                <Icon name="check" size={13} />
                {t("takeoff.runReady.approve", "Approve items")}
              </Button>
            ) : null}
            <Button variant="ghost" size="sm" onClick={() => navigate(`/app/takeoff/${projectId}/${drawing.id}`)}>
              {t("takeoff.runReady.measure", "Open Measure")}
            </Button>
          <div className="w-full">
              <ReadabilityChip value={row.readability} />
            </div>
          </li>
        ))}
      </ul>
      {open ? <ApprovePdfDialog projectId={projectId} drawingId={open.drawing.id} filename={open.drawing.original_filename} onClose={() => setOpen(null)} /> : null}
    </div>
  );
}

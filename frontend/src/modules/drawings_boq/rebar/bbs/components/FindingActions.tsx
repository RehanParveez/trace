import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../../organizations/components/OrganizationUi";
import { REASON_MAX } from "../utils/bbsAudit";
import { actionBlocked, availableActions, signSentence } from "../utils/bbsReport";
import type { Finding, FindingDecision } from "../types/bbsAudit.types";

interface FindingActionsProps {
  finding: Finding;
  pending: boolean;
  onDecide: (status: FindingDecision, reason: string) => void;
  onSign: (reason: string) => void;
}

export function FindingActions({ finding, pending, onDecide, onSign }: FindingActionsProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState(finding.reason ?? "");
  const actions = availableActions(finding);
  if (actions.length === 0) {
    return <p className="text-[12px] text-[var(--color-text-muted)]">{t("bbs.actions.signed", "This convention is signed for the project, so the finding is closed.")}</p>;
  }
  const blocked = pending || actionBlocked(reason) !== null;
  return (
    <div className="space-y-2" data-testid="finding-actions" onClick={(e) => e.stopPropagation()}>
      <textarea aria-label={t("bbs.reason", "Reason")} className="min-h-[56px] w-full rounded-[7px] border border-[var(--color-border)] bg-[var(--color-surface)] p-2 text-[12px]"
        placeholder={t("bbs.reasonRequired", "Why? A reason is required for every decision.")} maxLength={REASON_MAX} value={reason} onChange={(e) => setReason(e.target.value)} />
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" disabled={blocked} onClick={() => onDecide("ACCEPTED", reason.trim())}>{t("bbs.accept", "Accept")}</Button>
        <Button variant="ghost" size="sm" disabled={blocked} onClick={() => onDecide("REJECTED", reason.trim())}>{t("bbs.reject", "Reject")}</Button>
        {actions.includes("OPEN") ? <Button variant="ghost" size="sm" disabled={blocked} onClick={() => onDecide("OPEN", reason.trim())}>{t("bbs.reopen", "Reopen")}</Button> : null}
        {actions.includes("SIGN") ? <Button variant="primary" size="sm" disabled={blocked} onClick={() => onSign(reason.trim())}>{t("bbs.sign", "Sign the convention")}</Button> : null}
      </div>
      {actions.includes("SIGN") ? <p className="text-[11.5px] text-[var(--color-text-muted)]">{signSentence(finding)}</p> : null}
    </div>
  );
}

import { useMemo, useState } from "react";
import {Button, Icon, Modal,
} from "../../organizations/components/OrganizationUi";
import { useTranslation } from "react-i18next";

interface CancelSubscriptionDialogProps {
  isSubmitting?: boolean;
  onConfirm: (
    cancelAtPeriodEnd: boolean,
    idempotencyKey: string,
    reason?: string | null,
    feedback?: string | null,
  ) => void;
  onClose: () => void;
}

export function CancelSubscriptionDialog({
  isSubmitting = false,
  onConfirm,
  onClose,
}: CancelSubscriptionDialogProps) {
  const { t } = useTranslation();

  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState("");

  return (
    <Modal
      title={t("subscription.cancel.title")}
      description={t("subscription.cancel.description")}
      onClose={onClose}
    >
      <div className="space-y-4">
        <div>
         <label className="mb-1.5 block text-[12px] font-semibold text-[var(--color-text-secondary)]">
           Reason (optional)
         </label>
         <select
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          disabled={isSubmitting}
          className="w-full rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-[13px] outline-none focus:border-[var(--color-trace-gold)]"
         >
          <option value="">Select a reason…</option>
          <option value="too_expensive">Too expensive</option>
          <option value="missing_features">Missing features</option>
          <option value="switching_tool">Switching to another tool</option>
          <option value="temporary_pause">Temporary pause</option>
          <option value="other">Other</option>
         </select>
        </div>

      <div>
        <label className="mb-1.5 block text-[12px] font-semibold text-[var(--color-text-secondary)]">
          Additional feedback (optional)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={isSubmitting}
          rows={3}
          placeholder="Tell us more…"
          className="w-full rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-[13px] outline-none focus:border-[var(--color-trace-gold)]"
        />
      </div>

      <button
        type="button"
        disabled={isSubmitting}
        onClick={() =>
          onConfirm(true, idempotencyKey, reason.trim() || null, feedback.trim() || null)
        }
        className="flex w-full items-start gap-3.5 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left transition hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)] disabled:cursor-not-allowed disabled:opacity-50"
      >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
        <Icon name="settings" size={13} />
      </div>
      <div className="min-w-0">
       <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">
         {t("subscription.cancel.atPeriodEnd")}
       </div>
       <div className="mt-1 text-[12px] leading-4 text-[var(--color-text-secondary)]">
         {t("subscription.cancel.atPeriodEndDesc")}
       </div>
      </div>
      </button>

     <button
       type="button"
       disabled={isSubmitting}
       onClick={() =>
        onConfirm(false, idempotencyKey, reason.trim() || null, feedback.trim() || null)
       }
       className="flex w-full items-start gap-3.5 rounded-[var(--radius-md)] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] p-4 text-left transition hover:border-[var(--color-danger)]/60 disabled:cursor-not-allowed disabled:opacity-50"
      >
       <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-surface)] text-[var(--color-danger)]">
         <Icon name="lock" size={13} />
       </div>
       <div className="min-w-0">
        <div className="text-[13.5px] font-semibold text-[var(--color-danger)]">
          {t("subscription.cancel.immediately")}
        </div>
       <div className="mt-1 text-[12px] leading-4 text-[var(--color-text-secondary)]">
        {t("subscription.cancel.immediatelyDesc")}
       </div>
      </div>
    </button>

    <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
      <Button variant="ghost" onClick={onClose} disabled={isSubmitting}>
        {t("subscription.cancel.keep")}
      </Button>
    </div> 
   </div>
  </Modal>
 );
}

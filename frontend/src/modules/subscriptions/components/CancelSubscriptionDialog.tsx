import { useMemo } from "react";
import {Button, Icon, Modal,
} from "../../organizations/components/OrganizationUi";

interface CancelSubscriptionDialogProps {
  isSubmitting?: boolean;
  onConfirm: (
    cancelAtPeriodEnd: boolean,
    idempotencyKey: string,
  ) => void;
  onClose: () => void;
}

export function CancelSubscriptionDialog({
  isSubmitting = false,
  onConfirm,
  onClose,
}: CancelSubscriptionDialogProps) {
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  return (
    <Modal
      title="Cancel subscription"
      description="Choose when the organization's subscription should become inactive."
      onClose={onClose}
    >
      <div className="space-y-3.5">
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() =>
            onConfirm(true, idempotencyKey)
          }
          className="flex w-full items-start gap-3.5 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left transition hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-warning-bg)] text-[var(--color-warning)]">
            <Icon
              name="settings"
              size={13}
            />
          </div>

          <div className="min-w-0">
            <div className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">
              Cancel at period end
            </div>

            <div className="mt-1 text-[12px] leading-4 text-[var(--color-text-secondary)]">
              The organization keeps access through
              the current billing period, then the
              subscription is marked for cancellation.
            </div>
          </div>
        </button>

        <button
          type="button"
          disabled={isSubmitting}
          onClick={() =>
            onConfirm(false, idempotencyKey)
          }
          className="flex w-full items-start gap-3.5 rounded-[var(--radius-md)] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] p-4 text-left transition hover:border-[var(--color-danger)]/60 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[var(--color-surface)] text-[var(--color-danger)]">
            <Icon
              name="lock"
              size={13}
            />
          </div>

          <div className="min-w-0">
            <div className="text-[13.5px] font-semibold text-[var(--color-danger)]">
              Cancel immediately
            </div>

            <div className="mt-1 text-[12px] leading-4 text-[var(--color-text-secondary)]">
              The subscription becomes cancelled
              immediately and access to subscription-
              controlled operations may stop.
            </div>
          </div>
        </button>

        <div className="flex justify-end border-t border-[var(--color-border)] pt-4">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Keep subscription
          </Button>
        </div>
      </div>
    </Modal>
  );
}
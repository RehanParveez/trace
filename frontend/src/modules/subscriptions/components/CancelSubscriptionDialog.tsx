import {Button, Icon, Modal,
} from "../../organizations/components/OrganizationUi";

interface CancelSubscriptionDialogProps {
  isSubmitting?: boolean;
  onConfirm: (
    cancelAtPeriodEnd: boolean,
  ) => void;
  onClose: () => void;
}

export function CancelSubscriptionDialog({
  isSubmitting = false,
  onConfirm,
  onClose,
}: CancelSubscriptionDialogProps) {
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
            onConfirm(true)
          }
          className="flex w-full items-start gap-3.5 rounded-[10px] border border-[#e1d5bc] bg-white p-4 text-left transition hover:border-[#cdbd9c] hover:bg-[#fbf8f2] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[#fbefd9] text-[#b98626]">
            <Icon
              name="settings"
              size={13}
            />
          </div>

          <div className="min-w-0">
            <div className="text-[12px] font-semibold text-[#191410]">
              Cancel at period end
            </div>

            <div className="mt-1 text-[10.5px] leading-4 text-[#6b6152]">
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
            onConfirm(false)
          }
          className="flex w-full items-start gap-3.5 rounded-[10px] border border-[#efc5bd] bg-[#fff7f5] p-4 text-left transition hover:border-[#e2a89d] hover:bg-[#f9e5df] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-[#f9e5df] text-[#a33f31]">
            <Icon
              name="lock"
              size={13}
            />
          </div>

          <div className="min-w-0">
            <div className="text-[12px] font-semibold text-[#a33f31]">
              Cancel immediately
            </div>

            <div className="mt-1 text-[10.5px] leading-4 text-[#6b6152]">
              The subscription becomes cancelled
              immediately and access to subscription-
              controlled operations may stop.
            </div>
          </div>
        </button>

        <div className="flex justify-end border-t border-[#e1d5bc] pt-4">
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
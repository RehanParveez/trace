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
      <div className="space-y-3">
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() =>
            onConfirm(true)
          }
          className="flex w-full items-start gap-3 rounded-[10px] border border-[#e1d5bc] bg-white p-4 text-left transition hover:bg-[#f5efe3] disabled:opacity-50"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-[#fff4d9] text-[#b17a18]">
            <Icon
              name="settings"
              size={13}
            />
          </div>

          <div>
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
          className="flex w-full items-start gap-3 rounded-[10px] border border-[#efc5bd] bg-[#fff7f5] p-4 text-left transition hover:bg-[#f9e5df] disabled:opacity-50"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-white text-[#c24a3a]">
            <Icon
              name="lock"
              size={13}
            />
          </div>

          <div>
            <div className="text-[12px] font-semibold text-[#c24a3a]">
              Cancel immediately
            </div>

            <div className="mt-1 text-[10.5px] leading-4 text-[#7c7060]">
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
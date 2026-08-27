import type {Member,
} from "../types/organization.types";
import {Button, Icon, Modal,
} from "./OrganizationUi";
import {getMemberFullName,
} from "../utils/organization.utils";

interface MemberStatusDialogProps {
  member: Member;
  isSubmitting?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function MemberStatusDialog({
  member,
  isSubmitting = false,
  onConfirm,
  onClose,
}: MemberStatusDialogProps) {
  const activating =
    !member.is_active;

  return (
    <Modal
      title={
        activating
          ? "Activate member"
          : "Deactivate member"
      }
      description={
        activating
          ? "Restore this member's access to the organization."
          : "Remove this member's active access without deleting the member record."
      }
      onClose={onClose}
    >
      <div className="flex gap-3 rounded-[10px] border border-[#e1d5bc] bg-white p-4">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] ${
            activating
              ? "bg-[#e4f5ec] text-[#1e9d63]"
              : "bg-[#f9e5df] text-[#c24a3a]"
          }`}
        >
          <Icon
            name={
              activating
                ? "check"
                : "lock"
            }
            size={14}
          />
        </div>

        <div>
          <div className="text-[12px] font-semibold text-[#191410]">
            {getMemberFullName(
              member,
            )}
          </div>

          <p className="mt-1 text-[11px] leading-5 text-[#6b6152]">
            {activating
              ? "The member will become active again."
              : "The member will no longer be treated as an active organization user."}
          </p>
        </div>
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button
          variant="ghost"
          onClick={onClose}
        >
          Cancel
        </Button>

        <Button
          variant={
            activating
              ? "primary"
              : "danger"
          }
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          {isSubmitting
            ? "Saving…"
            : activating
              ? "Activate member"
              : "Deactivate member"}
        </Button>
      </div>
    </Modal>
  );
}
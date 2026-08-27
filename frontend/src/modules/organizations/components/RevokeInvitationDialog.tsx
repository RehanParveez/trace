import type {Invitation,
} from "../types/organization.types";
import {Button, Icon, Modal,
} from "./OrganizationUi";

interface RevokeInvitationDialogProps {
  invitation: Invitation;
  isSubmitting?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function RevokeInvitationDialog({
  invitation,
  isSubmitting = false,
  onConfirm,
  onClose,
}: RevokeInvitationDialogProps) {
  return (
    <Modal
      title="Revoke invitation"
      description="The invitation will no longer be usable by the recipient."
      onClose={onClose}
    >
      <div className="rounded-[10px] border border-[#e1d5bc] bg-white p-4">
        <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#a2957c]">
          Invitee
        </div>

        <div className="mt-1 text-[13px] font-semibold text-[#191410]">
          {invitation.email}
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
          variant="danger"
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          <Icon
            name="x"
            size={13}
          />

          {isSubmitting
            ? "Revoking…"
            : "Revoke invitation"}
        </Button>
      </div>
    </Modal>
  );
}
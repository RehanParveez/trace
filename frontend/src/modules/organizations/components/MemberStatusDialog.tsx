import type { Member } from "../types/organization.types";
import { Avatar, Badge, Button, Icon, Modal } from "./OrganizationUi";
import { getMemberFullName, getMemberInitials } from "../utils/organization.utils";

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
  const activating = !member.is_active;

  return (
    <Modal
      title={activating ? "Activate member" : "Deactivate member"}
      description={
        activating
          ? "Restore this member's access to the organization."
          : "Remove this member's active access without deleting the member record."
      }
      onClose={onClose}
    >
      <div className="flex items-center gap-3 rounded-[10px] border border-[#e1d5bc] bg-white p-4">
        <Avatar initials={getMemberInitials(member)} size="sm" />

        <div className="min-w-0 flex-1">
          <div className="truncate text-[12.5px] font-semibold text-[#191410]">
            {getMemberFullName(member)}
          </div>

          <div className="mt-0.5 truncate text-[10.5px] text-[#6b6152]">
            {member.email}
          </div>
        </div>

        <Badge tone={member.is_active ? "green" : "slate"}>
          {member.is_active ? "Active" : "Inactive"}
        </Badge>
      </div>

      <div
        className={`mt-3 flex gap-3 rounded-[10px] border p-4 ${
          activating
            ? "border-[#c9e9d7] bg-[#e4f5ec]"
            : "border-[#efc5bd] bg-[#fff7f5]"
        }`}
      >
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] ${
            activating
              ? "bg-white text-[#1e9d63]"
              : "bg-white text-[#c24a3a]"
          }`}
        >
          <Icon name={activating ? "check" : "lock"} size={14} />
        </div>

        <p className="text-[11.5px] leading-5 text-[#332a21]">
          {activating
            ? "The member will become active again and regain workspace access immediately."
            : "The member will no longer be treated as an active organization user and loses workspace access immediately."}
        </p>
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>

        <Button
          variant={activating ? "primary" : "danger"}
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

import type { Member } from "../types/organization.types";
import { Avatar, Badge, Button, Icon, Modal } from "./OrganizationUi";
import { getMemberFullName, getMemberInitials } from "../utils/organization.utils";
import { getApiErrorMessage } from "../../identity";
import { useTranslation } from "react-i18next";

interface MemberStatusDialogProps {
  member: Member;
  isSubmitting?: boolean;
  error?: unknown;
  onConfirm: () => void;
  onClose: () => void;
}

export function MemberStatusDialog({
  member,
  isSubmitting = false,
  error,
  onConfirm,
  onClose,
}: MemberStatusDialogProps) {
  const { t } = useTranslation();
  const activating = !member.is_active;

  return (
    <Modal
      title={activating ? t("members.activateTitle") : t("members.deactivateTitle")}
      description={
        activating
        ? t("members.activateDesc")
        : t("members.deactivateDesc") 
      }
      onClose={onClose}
    >
      {error ? (
        <div className="mb-3 flex items-center gap-2 rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
          <Icon name="alert" size={13} className="shrink-0" />
          {getApiErrorMessage(error, t("members.statusError"))}
        </div>
      ) : null}

      <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <Avatar initials={getMemberInitials(member)} size="sm" />

        <div className="min-w-0 flex-1">
          <div className="truncate text-[13.5px] font-semibold text-[var(--color-text-primary)]">
            {getMemberFullName(member)}
          </div>

          <div className="mt-0.5 truncate text-[12px] text-[var(--color-text-secondary)]">
            {member.email}
          </div>
        </div>

        <Badge tone={member.is_active ? "green" : "slate"}>
          {member.is_active ? t("members.active") : t("members.inactive")}
        </Badge>
      </div>

      <div
        className={`mt-3 flex gap-3 rounded-[var(--radius-md)] border p-4 ${
          activating
            ? "border-[var(--color-success)]/30 bg-[var(--color-success-bg)]"
            : "border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)]"
        }`}
      >
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] ${
            activating
              ? "bg-[var(--color-surface)] text-[var(--color-success)]"
              : "bg-[var(--color-surface)] text-[var(--color-danger)]"
          }`}
        >
          <Icon name={activating ? "check" : "lock"} size={14} />
        </div>

        <p className="text-[12.5px] leading-5 text-[var(--color-text-primary)]">
          {activating ? t("members.activateBody") : t("members.deactivateBody")}
        </p>
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
         {t("common.cancel")}
        </Button>

        <Button
          variant={activating ? "primary" : "danger"}
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          {isSubmitting
            ? t("members.activating")
            : activating
            ? t("members.activateConfirm")
            : t("members.deactivateConfirm")}
        </Button>
      </div>
    </Modal>
  );
}

import type { Invitation } from "../types/organization.types";
import { Button, Icon, Modal } from "./OrganizationUi";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  return (
    <Modal
      title={t("invitations.revokeTitle")}
      description={t("invitations.revokeDesc")}
      onClose={onClose}
    >
      <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-text-secondary)]">
          <Icon name="mail" size={14} />
        </div>

        <div className="min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {t("invitations.invitee")}
          </div>

          <div className="truncate text-[14px] font-semibold text-[var(--color-text-primary)]">
            {invitation.email}
          </div>
        </div>
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
         {t("common.cancel")}
        </Button>

        <Button variant="danger" onClick={onConfirm} disabled={isSubmitting}>
          <Icon name="x" size={13} />

          {isSubmitting ? t("invitations.revoking") : t("invitations.revokeConfirm")}
        </Button>
      </div>
    </Modal>
  );
}

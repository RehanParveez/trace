import type { ReactNode } from "react";
import { Button, Modal } from "../../organizations/components/OrganizationUi";
import { useTranslation } from "react-i18next";

interface ConfirmDialogProps {
  title: string;
  description?: string;
  confirmLabel: string;
  pending: boolean;
  error?: string | null;
  children?: ReactNode;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmDialog({ title, description, confirmLabel, pending, error, children, onConfirm, onClose }: ConfirmDialogProps) {
  const { t } = useTranslation();
  return (
    <Modal title={title} description={description} onClose={onClose}>
      <div className="space-y-4">
        {children}
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={pending}>{t("common.cancel", "Cancel")}</Button>
          <Button variant="primary" onClick={onConfirm} disabled={pending}>{confirmLabel}</Button>
        </div>
      </div>
    </Modal>
  );
}

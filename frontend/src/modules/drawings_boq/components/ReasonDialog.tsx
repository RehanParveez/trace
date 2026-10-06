import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal } from "../../organizations/components/OrganizationUi";
import { useTranslation } from "react-i18next";

interface ReasonDialogProps {
  title: string;
  description?: string;
  label: string;
  required: boolean;
  confirmLabel: string;
  pending: boolean;
  error: string | null;
  onConfirm: (text: string) => void;
  onClose: () => void;
}

export function ReasonDialog({ title, description, label, required, confirmLabel, pending, error, onConfirm, onClose }: ReasonDialogProps) {
  const { t } = useTranslation();
  const [text, setText] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onConfirm(text.trim());
  }

  return (
    <Modal title={title} description={description} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label={label}>
          <textarea className={`${inputClass} min-h-[88px]`} value={text} maxLength={1000} required={required} onChange={(e) => setText(e.target.value)} />
        </Field>
        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}
        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button variant="ghost" onClick={onClose} disabled={pending}>{t("common.cancel", "Cancel")}</Button>
          <Button type="submit" variant="primary" disabled={pending || (required && !text.trim())}>{confirmLabel}</Button>
        </div>
      </form>
    </Modal>
  );
}

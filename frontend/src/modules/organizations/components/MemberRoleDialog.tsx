import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { Member, Role } from "../types/organization.types";
import {Avatar, Badge, Button, Icon, Modal,
} from "./OrganizationUi";
import {getMemberFullName, getMemberInitials,
} from "../utils/organization.utils";
import { getApiErrorMessage } from "../../identity";
import { useTranslation } from "react-i18next";

interface MemberRoleDialogProps {
  member: Member;
  roles: Role[];
  isSubmitting?: boolean;
  error?: unknown;
  onSubmit: (roleId: string) => void;
  onClose: () => void;
}

export function MemberRoleDialog({
  member,
  roles,
  isSubmitting = false,
  error,
  onSubmit,
  onClose,
}: MemberRoleDialogProps) {
  const { t } = useTranslation();
  const [roleId, setRoleId] = useState(member.role.id);

  useEffect(() => {
    setRoleId(member.role.id);
  }, [member.role.id]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    onSubmit(roleId);
  }

  return (
    <Modal
      title={t("members.roleDialog.title")}
      description={t("members.roleDialog.description", { email: member.email })}
      onClose={onClose}
    >
     <form onSubmit={handleSubmit} className="space-y-4">
        {error ? (
          <div className="flex items-center gap-2 rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            <Icon name="alert" size={13} className="shrink-0" />
            {getApiErrorMessage(error, t("members.roleDialog.error"))}
          </div>
        ) : null}

        <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
          <Avatar initials={getMemberInitials(member)} size="sm" />

          <div className="min-w-0">
            <div className="truncate text-[13px] font-semibold text-[var(--color-text-primary)]">
              {getMemberFullName(member)}
            </div>

            <div className="mt-0.5 text-[12px] text-[var(--color-text-secondary)]">
              {t("members.roleDialog.currently")}{" "}
              <span className="font-semibold text-[var(--color-text-primary)]">
                {member.role.name}
              </span>
            </div>
          </div>
        </div>

        <div>
          <span className="mb-1.5 block text-[12px] font-bold uppercase tracking-[0.04em] text-[var(--color-text-secondary)]">
            {t("members.roleDialog.roleLabel")}
          </span>

          <div className="max-h-64 space-y-2 overflow-y-auto pr-0.5">
            {roles.map((role) => {
              const selected = roleId === role.id;

              return (
                <label
                  key={role.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-[var(--radius-md)] border p-3 transition ${
                    selected
                      ? "border-[var(--color-trace-gold)] bg-[var(--color-warning-bg)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)]"
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    className="sr-only"
                    checked={selected}
                    onChange={() => setRoleId(role.id)}
                  />

                  <span
                    className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 ${
                      selected
                        ? "border-[var(--color-trace-gold-dark)]"
                        : "border-[var(--color-border-strong)]"
                    }`}
                  >
                    {selected ? (
                      <span className="h-2 w-2 rounded-full bg-[var(--color-trace-gold)]" />
                    ) : null}
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-[13.5px] font-semibold text-[var(--color-text-primary)]">
                        {role.name}
                      </span>

                      <Badge tone={role.is_system ? "blue" : "slate"}>
                        {role.is_system ? t("roles.system") : t("roles.custom")}
                      </Badge>
                    </span>

                    <span className="mt-0.5 block font-mono text-[11px] text-[var(--color-text-muted)]">
                      {t("roles.permissionsCount", { count: role.permissions.length })}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting || !roleId}
          >
            <Icon name="check" size={13} />

            {isSubmitting ? "Saving…" : "Save role"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

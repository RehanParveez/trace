import { useState } from "react";
import type { FormEvent } from "react";
import type { Role } from "../types/organization.types";
import {Badge, Button, Field, Icon, inputClass, Panel, PanelHeader,
} from "./OrganizationUi";
import { useTranslation } from "react-i18next";

interface InvitationFormProps {
  roles: Role[];
  isSubmitting?: boolean;
  onSubmit: (email: string, roleId: string) => void;
  onCancel?: () => void;
}

export function InvitationForm({
  roles,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: InvitationFormProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [roleId, setRoleId] = useState(roles[0]?.id ?? "");

  const selectedRole = roles.find((role) => role.id === roleId);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    onSubmit(email.trim().toLowerCase(), roleId);
  }

  return (
    <Panel>
      <PanelHeader
       eyebrow={t("invitations.formEyebrow")}
       title={t("invitations.formTitle")}
       description={t("invitations.formDesc")}
      />

      <form
        onSubmit={handleSubmit}
        className="grid gap-4 p-5 md:grid-cols-[1.4fr_1fr_auto] md:items-end"
      >
        <Field label={t("invitations.emailLabel")}>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            className={inputClass}
            placeholder={t("invitations.emailPlaceholder")}
            autoFocus
          />
        </Field>

        <Field label={t("invitations.roleLabel")}>
          <select
            value={roleId}
            onChange={(event) => setRoleId(event.target.value)}
            required
            className={inputClass}
          >
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </Field>

        <div className="flex justify-end gap-2">
          {onCancel ? (
            <Button type="button" variant="ghost" onClick={onCancel}>
              {t("common.cancel")}
            </Button>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting || !roleId}
          >
            <Icon name="mail" size={13} />

            {isSubmitting ? t("invitations.sending") : t("invitations.send")}
          </Button>
        </div>

        {selectedRole ? (
          <div className="flex items-center gap-2 md:col-span-3">
            <span className="text-[12px] text-[var(--color-text-secondary)]">
              {t("invitations.grants")}
            </span>

            <Badge tone={selectedRole.is_system ? "blue" : "slate"}>
              {selectedRole.name} ·{" "}
              {selectedRole.is_system ? t("roles.system") : t("roles.custom")}
            </Badge>

            <span className="font-mono text-[11px] text-[var(--color-text-muted)]">
              {t("roles.permissionsCount", { count: selectedRole.permissions.length })}
            </span>
          </div>
        ) : null}
      </form>
    </Panel>
  );
}

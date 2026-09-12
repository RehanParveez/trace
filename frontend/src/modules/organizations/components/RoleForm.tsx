import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type {Permission, Role, RoleCreateRequest, RoleUpdateRequest,
} from "../types/organization.types";
import {Button, Field, Icon, inputClass, Panel, PanelHeader,
} from "./OrganizationUi";
import { PermissionSelector } from "./PermissionSelector";
import { useTranslation } from "react-i18next";

interface RoleFormProps {
  role?: Role;
  permissions: Permission[];
  isSubmitting?: boolean;
  onSubmit: (payload: RoleCreateRequest | RoleUpdateRequest) => void;
  onCancel?: () => void;
}

export function RoleForm({
  role,
  permissions,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: RoleFormProps) {
  const { t } = useTranslation();
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<
    string[]
  >(role?.permissions.map((permission) => permission.id) ?? []);

  useEffect(() => {
    setName(role?.name ?? "");
    setDescription(role?.description ?? "");
    setSelectedPermissionIds(
      role?.permissions.map((permission) => permission.id) ?? [],
    );
  }, [role]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    onSubmit({
      name: name.trim(),
      description: description.trim() || null,
      permission_ids: selectedPermissionIds,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Panel>
        <PanelHeader
          eyebrow={role ? t("roles.configEyebrow") : t("roles.newEyebrow")}
          title={role ? t("roles.editTitle", { name: role.name }) : t("roles.createTitle")}
          description={
            role?.is_system
            ? t("roles.systemProtected")
            : t("roles.defineBoundary")
          }
        />

        {role?.is_system ? (
          <div className="mx-5 mt-5 flex items-center gap-2.5 rounded-[8px] border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] px-3 py-2.5 text-[12px] font-medium text-[var(--color-info)]">
            <Icon name="lock" size={13} />
            {t("roles.systemRoleBanner")}
          </div>
        ) : null}

        <div className="grid gap-4 p-5 md:grid-cols-2">
          <Field label={t("roles.nameLabel")}>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              minLength={2}
              maxLength={100}
              required
              disabled={role?.is_system}
              className={inputClass}
              placeholder={t("roles.namePlaceholder")}
            />
          </Field>

          <Field
            label={t("roles.descriptionLabel")}
            hint={t("roles.descriptionHint")}
          >
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={500}
              disabled={role?.is_system}
              className={inputClass}
              placeholder={t("roles.descriptionPlaceholder")}
            />
          </Field>
        </div>
      </Panel>

      <Panel>
        <div className="p-5">
          <PermissionSelector
            permissions={permissions}
            selectedIds={selectedPermissionIds}
            disabled={role?.is_system}
            onChange={setSelectedPermissionIds}
          />
        </div>
      </Panel>

      {!role?.is_system ? (
        <div className="flex justify-end gap-2">
          {onCancel ? (
            <Button type="button" variant="ghost" onClick={onCancel}>
             {t("common.cancel")}
            </Button>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting || name.trim().length < 2}
          >
            <Icon name="check" size={13} />

            {isSubmitting ? t("roles.saving") : role ? t("roles.saveRole") : t("roles.createRole")}
          </Button>
        </div>
      ) : null}
    </form>
  );
}

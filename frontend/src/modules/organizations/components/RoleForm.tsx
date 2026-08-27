import {useEffect, useState,
} from "react";
import type { FormEvent } from "react";
import type {Permission, Role, RoleCreateRequest, RoleUpdateRequest,
} from "../types/organization.types";
import { Button, Field, Icon, inputClass, Panel, PanelHeader,
} from "./OrganizationUi";
import {PermissionSelector,
} from "./PermissionSelector";

interface RoleFormProps {
  role?: Role;
  permissions: Permission[];
  isSubmitting?: boolean;
  onSubmit: (
    payload:
      | RoleCreateRequest
      | RoleUpdateRequest,
  ) => void;
  onCancel?: () => void;
}

export function RoleForm({
  role,
  permissions,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: RoleFormProps) {
  const [name, setName] =
    useState(role?.name ?? "");

  const [description, setDescription] =
    useState(
      role?.description ?? "",
    );

  const [
    selectedPermissionIds,
    setSelectedPermissionIds,
  ] = useState<string[]>(
    role?.permissions.map(
      (permission) =>
        permission.id,
    ) ?? [],
  );

  useEffect(() => {
    setName(
      role?.name ?? "",
    );

    setDescription(
      role?.description ?? "",
    );

    setSelectedPermissionIds(
      role?.permissions.map(
        (permission) =>
          permission.id,
      ) ?? [],
    );
  }, [role]);

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    onSubmit({
      name: name.trim(),
      description:
        description.trim() ||
        null,
      permission_ids:
        selectedPermissionIds,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <Panel>
        <PanelHeader
          eyebrow={
            role
              ? "ROLE CONFIGURATION"
              : "NEW ACCESS ROLE"
          }
          title={
            role
              ? `Edit ${role.name}`
              : "Create a role"
          }
          description={
            role?.is_system
              ? "System roles are protected by the platform and cannot be structurally changed."
              : "Define a clear role boundary first, then assign the exact permissions it needs."
          }
        />

        <div className="grid gap-4 p-5 md:grid-cols-2">
          <Field label="Role name">
            <input
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value,
                )
              }
              minLength={2}
              maxLength={100}
              required
              disabled={
                role?.is_system
              }
              className={inputClass}
              placeholder="e.g. Procurement Officer"
            />
          </Field>

          <Field
            label="Description"
            hint="Keep the description operational and role-focused."
          >
            <input
              value={description}
              onChange={(event) =>
                setDescription(
                  event.target.value,
                )
              }
              maxLength={500}
              disabled={
                role?.is_system
              }
              className={inputClass}
              placeholder="What this role is responsible for"
            />
          </Field>
        </div>
      </Panel>

      <Panel>
        <div className="p-5">
          <PermissionSelector
            permissions={
              permissions
            }
            selectedIds={
              selectedPermissionIds
            }
            disabled={
              role?.is_system
            }
            onChange={
              setSelectedPermissionIds
            }
          />
        </div>
      </Panel>

      {!role?.is_system ? (
        <div className="flex justify-end gap-2">
          {onCancel ? (
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
            >
              Cancel
            </Button>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            disabled={
              isSubmitting ||
              name.trim().length < 2
            }
          >
            <Icon
              name="check"
              size={13}
            />

            {isSubmitting
              ? "Saving…"
              : role
                ? "Save role"
                : "Create role"}
          </Button>
        </div>
      ) : null}
    </form>
  );
}
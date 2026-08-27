import {useState,
} from "react";
import type { FormEvent } from "react";
import type {Role,
} from "../types/organization.types";
import {Button, Field, Icon, inputClass, Panel, PanelHeader,
} from "./OrganizationUi";

interface InvitationFormProps {
  roles: Role[];
  isSubmitting?: boolean;
  onSubmit: (
    email: string,
    roleId: string,
  ) => void;
  onCancel?: () => void;
}

export function InvitationForm({
  roles,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: InvitationFormProps) {
  const [email, setEmail] =
    useState("");

  const [roleId, setRoleId] =
    useState(
      roles[0]?.id ?? "",
    );

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    onSubmit(
      email.trim().toLowerCase(),
      roleId,
    );
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="ACCESS REQUEST"
        title="Invite a team member"
        description="Send an organization invitation and assign the intended access role before the user joins."
      />

      <form
        onSubmit={handleSubmit}
        className="grid gap-4 p-5 md:grid-cols-[1.4fr_1fr_auto] md:items-end"
      >
        <Field label="Email address">
          <input
            type="email"
            value={email}
            onChange={(event) =>
              setEmail(
                event.target.value,
              )
            }
            required
            className={inputClass}
            placeholder="name@company.com"
            autoFocus
          />
        </Field>

        <Field label="Role">
          <select
            value={roleId}
            onChange={(event) =>
              setRoleId(
                event.target.value,
              )
            }
            required
            className={inputClass}
          >
            {roles.map(
              (role) => (
                <option
                  key={role.id}
                  value={role.id}
                >
                  {role.name}
                </option>
              ),
            )}
          </select>
        </Field>

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
              !roleId
            }
          >
            <Icon
              name="mail"
              size={13}
            />

            {isSubmitting
              ? "Sending…"
              : "Send invitation"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
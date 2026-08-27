import {useEffect, useState,
} from "react";
import type { FormEvent } from "react";
import type {Member, Role,
} from "../types/organization.types";
import {Button, Field, Icon, inputClass, Modal,
} from "./OrganizationUi";

interface MemberRoleDialogProps {
  member: Member;
  roles: Role[];
  isSubmitting?: boolean;
  onSubmit: (
    roleId: string,
  ) => void;
  onClose: () => void;
}

export function MemberRoleDialog({
  member,
  roles,
  isSubmitting = false,
  onSubmit,
  onClose,
}: MemberRoleDialogProps) {
  const [roleId, setRoleId] =
    useState(member.role.id);

  useEffect(() => {
    setRoleId(
      member.role.id,
    );
  }, [
    member.role.id,
  ]);

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    onSubmit(roleId);
  }

  return (
    <Modal
      title="Change member role"
      description={`Update the access role assigned to ${member.email}.`}
      onClose={onClose}
    >
      <form
        onSubmit={handleSubmit}
        className="space-y-4"
      >
        <Field label="Organization role">
          <select
            value={roleId}
            onChange={(event) =>
              setRoleId(
                event.target.value,
              )
            }
            className={inputClass}
          >
            {roles.map(
              (role) => (
                <option
                  key={role.id}
                  value={role.id}
                >
                  {role.name}
                  {role.is_system
                    ? " · System"
                    : ""}
                </option>
              ),
            )}
          </select>
        </Field>

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
          >
            Cancel
          </Button>

          <Button
            type="submit"
            variant="primary"
            disabled={
              isSubmitting ||
              !roleId
            }
          >
            <Icon
              name="check"
              size={13}
            />

            {isSubmitting
              ? "Saving…"
              : "Save role"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
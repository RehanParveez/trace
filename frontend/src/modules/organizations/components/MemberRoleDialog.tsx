import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { Member, Role } from "../types/organization.types";
import {Avatar, Badge, Button, Icon, Modal,
} from "./OrganizationUi";
import {getMemberFullName, getMemberInitials,
} from "../utils/organization.utils";
import { getApiErrorMessage } from "../../identity";

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
      title="Change member role"
      description={`Update the access role assigned to ${member.email}.`}
      onClose={onClose}
    >
     <form onSubmit={handleSubmit} className="space-y-4">
        {error ? (
          <div className="flex items-center gap-2 rounded-[8px] border border-[#efc5bd] bg-[#fff7f5] px-3 py-2 text-[11px] text-[#c24a3a]">
            <Icon name="alert" size={13} className="shrink-0" />
            {getApiErrorMessage(error, "Couldn't change this member's role.")}
          </div>
        ) : null}

        <div className="flex items-center gap-3 rounded-[10px] border border-[#e1d5bc] bg-white p-3">
          <Avatar initials={getMemberInitials(member)} size="sm" />

          <div className="min-w-0">
            <div className="truncate text-[12.5px] font-semibold text-[#191410]">
              {getMemberFullName(member)}
            </div>

            <div className="mt-0.5 text-[10.5px] text-[#6b6152]">
              Currently{" "}
              <span className="font-semibold text-[#332a21]">
                {member.role.name}
              </span>
            </div>
          </div>
        </div>

        <div>
          <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-[0.04em] text-[#6b6152]">
            Organization role
          </span>

          <div className="max-h-64 space-y-2 overflow-y-auto pr-0.5">
            {roles.map((role) => {
              const selected = roleId === role.id;

              return (
                <label
                  key={role.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-[10px] border p-3 transition ${
                    selected
                      ? "border-[#d9a441] bg-[#fbefd9]"
                      : "border-[#e1d5bc] bg-white hover:bg-[#f5efe3]"
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
                        ? "border-[#b98626]"
                        : "border-[#cbbb9c]"
                    }`}
                  >
                    {selected ? (
                      <span className="h-2 w-2 rounded-full bg-[#d9a441]" />
                    ) : null}
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-[12.5px] font-semibold text-[#332a21]">
                        {role.name}
                      </span>

                      <Badge tone={role.is_system ? "blue" : "slate"}>
                        {role.is_system ? "System" : "Custom"}
                      </Badge>
                    </span>

                    <span className="mt-0.5 block font-mono text-[10px] text-[#a2957c]">
                      {role.permissions.length} permission
                      {role.permissions.length === 1 ? "" : "s"}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
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

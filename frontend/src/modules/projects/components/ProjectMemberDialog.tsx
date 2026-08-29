import { useState } from "react";
import type{ FormEvent } from "react";
import {Button,
} from "../../organizations/components/OrganizationUi";
import {useAddProjectMember,
} from "../hooks";
import type {ProjectMemberRole,
} from "../types/project.types";

const roles: ProjectMemberRole[] = [
  "MANAGER",
  "ENGINEER",
  "SUPERVISOR",
  "SITE_MANAGER",
  "MEMBER",
];

interface ProjectMemberDialogProps {
  projectId: string;
  onClose: () => void;
}

export function ProjectMemberDialog({
  projectId,
  onClose,
}: ProjectMemberDialogProps) {
  const addMember =
    useAddProjectMember();

  const [userId, setUserId] =
    useState("");

  const [role, setRole] =
    useState<ProjectMemberRole>(
      "MEMBER",
    );

  function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    addMember.mutate(
      {
        projectId,
        payload: {
          user_id: userId.trim(),
          role,
        },
      },
      {
        onSuccess: onClose,
      },
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#16283f]/45 p-4 backdrop-blur-[2px]">
      <div className="w-full max-w-md rounded-[12px] border border-[#d9ceb9] bg-[#fbf8f2] shadow-[0_24px_70px_rgba(20,25,35,0.22)]">
        <div className="border-b border-[#e1d5bc] p-5">
          <div className="text-[9px] font-bold uppercase tracking-[0.14em] text-[#a2957c]">
            PROJECT TEAM
          </div>

          <h2 className="mt-1 font-[Archivo] text-[20px] font-bold text-[#191410]">
            Add project member
          </h2>
        </div>

        <form
          onSubmit={submit}
          className="space-y-5 p-5"
        >
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              User ID
            </span>

            <input
              value={userId}
              onChange={(event) =>
                setUserId(
                  event.target.value,
                )
              }
              placeholder="User UUID"
              required
              className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 font-mono text-[10.5px] text-[#191410] outline-none focus:border-[#c39a38]"
            />
          </label>

          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              Project role
            </span>

            <select
              value={role}
              onChange={(event) =>
                setRole(
                  event.target
                    .value as ProjectMemberRole,
                )
              }
              className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
            >
              {roles.map(
                (item) => (
                  <option
                    key={item}
                    value={item}
                  >
                    {item.replace(
                      "_",
                      " ",
                    )}
                  </option>
                ),
              )}
            </select>
          </label>

          <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={
                addMember.isPending
              }
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="primary"
              disabled={
                addMember.isPending ||
                !userId.trim()
              }
            >
              {addMember.isPending
                ? "Adding..."
                : "Add member"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
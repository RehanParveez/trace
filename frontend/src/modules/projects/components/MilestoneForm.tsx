import { useState } from "react";
import type { FormEvent } from "react";
import {Button,
} from "../../organizations/components/OrganizationUi";
import {useCreateMilestone, useUpdateMilestone,
} from "../hooks";
import type {Milestone,
} from "../types/project.types";

interface MilestoneFormProps {
  projectId: string;
  milestone?: Milestone;
  onClose: () => void;
}

export function MilestoneForm({
  projectId,
  milestone,
  onClose,
}: MilestoneFormProps) {
  const createMilestone =
    useCreateMilestone();

  const updateMilestone =
    useUpdateMilestone();

  const [name, setName] =
    useState(milestone?.name ?? "");

  const [description, setDescription] =
    useState(
      milestone?.description ?? "",
    );

  const [dueDate, setDueDate] =
    useState(
      milestone?.due_date ?? "",
    );

  const editing = Boolean(milestone);

  const isSubmitting =
    createMilestone.isPending ||
    updateMilestone.isPending;

  function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const payload = {
      name: name.trim(),
      description:
        description.trim() || null,
      due_date: dueDate || null,
    };

    if (editing && milestone) {
      updateMilestone.mutate(
        {
          projectId,
          milestoneId: milestone.id,
          payload,
        },
        {
          onSuccess: onClose,
        },
      );

      return;
    }

    createMilestone.mutate(
      {
        projectId,
        payload,
      },
      {
        onSuccess: onClose,
      },
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#16283f]/45 p-4 backdrop-blur-[2px]">
      <div className="w-full max-w-lg rounded-[12px] border border-[#d9ceb9] bg-[#fbf8f2] shadow-[0_24px_70px_rgba(20,25,35,0.22)]">
        <div className="border-b border-[#e1d5bc] p-5">
          <div className="text-[9px] font-bold uppercase tracking-[0.14em] text-[#a2957c]">
            DELIVERY TRACK
          </div>

          <h2 className="mt-1 font-[Archivo] text-[20px] font-bold text-[#191410]">
            {editing
              ? "Edit milestone"
              : "Add milestone"}
          </h2>
        </div>

        <form
          onSubmit={submit}
          className="space-y-5 p-5"
        >
          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              Milestone name *
            </span>

            <input
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value,
                )
              }
              required
              placeholder="Foundation complete"
              className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
            />
          </label>

          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              Description
            </span>

            <textarea
              value={description}
              onChange={(event) =>
                setDescription(
                  event.target.value,
                )
              }
              rows={4}
              placeholder="Milestone details"
              className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[11px] text-[#191410] outline-none focus:border-[#c39a38]"
            />
          </label>

          <label className="block">
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#756957]">
              Due date
            </span>

            <input
              type="date"
              value={dueDate}
              onChange={(event) =>
                setDueDate(
                  event.target.value,
                )
              }
              className="mt-1.5 w-full rounded-[8px] border border-[#d9ceb9] bg-white px-3 py-2.5 text-[10.5px] text-[#191410] outline-none focus:border-[#c39a38]"
            />
          </label>

          <div className="flex justify-end gap-2 border-t border-[#e1d5bc] pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="primary"
              disabled={
                isSubmitting ||
                !name.trim()
              }
            >
              {isSubmitting
                ? "Saving..."
                : editing
                  ? "Save changes"
                  : "Add milestone"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
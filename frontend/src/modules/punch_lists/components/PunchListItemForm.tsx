import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal, useToast } from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useMembers } from "../../organizations";
import { useSubcontractors } from "../../subcontractors";
import { useAddPunchListItem } from "../hooks";

export function PunchListItemForm({ projectId, punchListId, onClose }: {
  projectId: string; punchListId: string; onClose: () => void;
}) {
  const membersQuery = useMembers(0, 100);
  const subsQuery = useSubcontractors();
  const addItem = useAddPunchListItem(projectId, punchListId);
  const { showToast } = useToast();

  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [assigneeType, setAssigneeType] = useState<"none" | "member" | "subcontractor">("none");
  const [assigneeId, setAssigneeId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const members = membersQuery.data?.items ?? [];
  const subcontractors = subsQuery.data ?? [];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    addItem.mutate(
      {
        location: location.trim(), description: description.trim(),
        assigned_to_user_id: assigneeType === "member" ? assigneeId : null,
        assigned_to_subcontractor_id: assigneeType === "subcontractor" ? assigneeId : null,
        due_date: dueDate || null,
      },
      {
        onSuccess: () => { onClose(); showToast({ tone: "success", title: "Item added" }); },
        onError: (e) => setError(getApiErrorMessage(e, "Couldn't add this item.")),
      },
    );
  }

  return (
    <Modal title="Add punch list item" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Location"><input required className={inputClass} value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Room 204, 3rd floor" /></Field>
        <Field label="Description"><textarea required className={`${inputClass} resize-y`} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Door doesn't close properly" /></Field>

        <Field label="Assign to">
          <select className={inputClass} value={assigneeType} onChange={(e) => { setAssigneeType(e.target.value as typeof assigneeType); setAssigneeId(""); }}>
            <option value="none">Unassigned</option>
            <option value="member">Team member</option>
            <option value="subcontractor">Subcontractor</option>
          </select>
        </Field>

        {assigneeType === "member" ? (
          <Field label="Team member">
            <select className={inputClass} value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
              <option value="">Select a member</option>
              {members.map((m: any) => <option key={m.id} value={m.id}>{m.first_name} {m.last_name}</option>)}
            </select>
          </Field>
        ) : null}

        {assigneeType === "subcontractor" ? (
          <Field label="Subcontractor">
            <select className={inputClass} value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
              <option value="">Select a subcontractor</option>
              {subcontractors.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.trade_specialization})</option>)}
            </select>
          </Field>
        ) : null}

        <Field label="Due date (optional)"><input type="date" className={inputClass} value={dueDate} onChange={(e) => setDueDate(e.target.value)} /></Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={addItem.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={addItem.isPending || !location.trim() || !description.trim()}>{addItem.isPending ? "Adding…" : "Add item"}</Button>
        </div>
      </form>
    </Modal>
  );
}
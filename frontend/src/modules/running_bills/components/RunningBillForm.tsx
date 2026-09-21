import { useState } from "react";
import type { FormEvent } from "react";
import {Button, Field, inputClass, Modal, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBOQVersions } from "../../drawings_boq";
import { useCreateRunningBill } from "../hooks";

interface RunningBillFormProps {
  projectId: string;
  onClose: () => void;
}

export function RunningBillForm({ projectId, onClose }: RunningBillFormProps) {
  const boqVersionsQuery = useBOQVersions(projectId);
  const createBill = useCreateRunningBill();
  const { showToast } = useToast();

  const boqVersions = boqVersionsQuery.data ?? [];

  const [boqVersionId, setBoqVersionId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(() =>
    new Date().toISOString().slice(0, 10),
  );
  const [retentionPercentage, setRetentionPercentage] = useState("10");
  const [retentionCapPercentage, setRetentionCapPercentage] = useState("");
  const [advanceRecovery, setAdvanceRecovery] = useState("0");
  const [otherDeductions, setOtherDeductions] = useState("0");
  const [otherDeductionsNote, setOtherDeductionsNote] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const activeBoqVersionId = boqVersionId || boqVersions[0]?.id || "";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createBill.mutate(
      {
        project_id: projectId,
        boq_version_id: activeBoqVersionId,
        period_start: periodStart,
        period_end: periodEnd,
        retention_percentage: Number(retentionPercentage),
        retention_cap_percentage:
          retentionCapPercentage === ""
            ? null
            : Number(retentionCapPercentage),
        advance_recovery_amount: Number(advanceRecovery),
        other_deductions_amount: Number(otherDeductions),
        other_deductions_note: otherDeductionsNote.trim() || null,
        notes: notes.trim() || null,
      },
      {
        onSuccess: () => {
          onClose();
          showToast({
            tone: "success",
            title: "Running bill generated as a draft",
          });
        },
        onError: (mutationError) =>
          setError(
            getApiErrorMessage(
              mutationError,
              "Couldn't generate this bill. Please try again.",
            ),
          ),
      },
    );
  }

  return (
    <Modal
      title="Generate running bill"
      description="Pulls approved progress claims for this BOQ version into a client-billable running bill / IPC."
      onClose={onClose}
      wide
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="BOQ version">
          <select
            className={inputClass}
            value={activeBoqVersionId}
            onChange={(e) => setBoqVersionId(e.target.value)}
          >
            {boqVersions.length === 0 ? (
              <option value="">No BOQ versions available</option>
            ) : null}
            {boqVersions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.label}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Period start">
            <input
              type="date"
              required
              className={inputClass}
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
            />
          </Field>
          <Field label="Period end">
            <input
              type="date"
              required
              className={inputClass}
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Retention %" hint="Standard practice is 5-10%">
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              required
              className={inputClass}
              value={retentionPercentage}
              onChange={(e) => setRetentionPercentage(e.target.value)}
            />
          </Field>
          <Field
            label="Retention cap % (optional)"
            hint="Stop deducting once cumulative retention hits this % of contract value"
          >
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              className={inputClass}
              value={retentionCapPercentage}
              onChange={(e) => setRetentionCapPercentage(e.target.value)}
              placeholder="No cap"
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Advance recovery (PKR)">
            <input
              type="number"
              step="any"
              min="0"
              className={inputClass}
              value={advanceRecovery}
              onChange={(e) => setAdvanceRecovery(e.target.value)}
            />
          </Field>
          <Field label="Other deductions (PKR)">
            <input
              type="number"
              step="any"
              min="0"
              className={inputClass}
              value={otherDeductions}
              onChange={(e) => setOtherDeductions(e.target.value)}
            />
          </Field>
        </div>

        {Number(otherDeductions) > 0 ? (
          <Field label="Other deductions note">
            <input
              className={inputClass}
              value={otherDeductionsNote}
              onChange={(e) => setOtherDeductionsNote(e.target.value)}
              placeholder="e.g. WHT @ 7%"
            />
          </Field>
        ) : null}

        <Field label="Notes">
          <textarea
            className={`${inputClass} resize-y`}
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </Field>

        {error ? (
          <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={createBill.isPending}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              createBill.isPending ||
              !activeBoqVersionId ||
              !periodStart ||
              !periodEnd
            }
          >
            {createBill.isPending ? "Generating…" : "Generate bill (draft)"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
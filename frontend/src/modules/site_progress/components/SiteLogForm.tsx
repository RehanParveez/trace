import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, inputClass, Modal } from "../../organizations/components/OrganizationUi";
import { useCreateSiteLog } from "../hooks";

interface SiteLogFormProps {
  projectId: string;
  onClose: () => void;
}

export function SiteLogForm({ projectId, onClose }: SiteLogFormProps) {
  const createLog = useCreateSiteLog();

  const [logDate, setLogDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [workforceCount, setWorkforceCount] = useState("");
  const [weather, setWeather] = useState("");
  const [blockers, setBlockers] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    createLog.mutate(
      {
        project_id: projectId,
        log_date: logDate,
        workforce_count: workforceCount === "" ? null : Number(workforceCount),
        weather: weather.trim() || null,
        blockers: blockers.trim() || null,
        notes: notes.trim() || null,
      },
      {
        onSuccess: onClose,
        onError: () => setError("Couldn't save this site log. Please try again."),
      },
    );
  }

  return (
    <Modal title="New site log" description="Record today's progress, workforce and any blockers from the field." onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Log date">
            <input type="date" required className={inputClass} value={logDate} onChange={(e) => setLogDate(e.target.value)} />
          </Field>
          <Field label="Workforce on site">
            <input type="number" min="0" className={inputClass} value={workforceCount} onChange={(e) => setWorkforceCount(e.target.value)} placeholder="e.g. 24" />
          </Field>
        </div>

        <Field label="Weather">
          <input className={inputClass} value={weather} onChange={(e) => setWeather(e.target.value)} placeholder="e.g. Clear, no delays" />
        </Field>

        <Field label="Blockers">
          <textarea className={`${inputClass} resize-y`} rows={2} value={blockers} onChange={(e) => setBlockers(e.target.value)} placeholder="Anything holding up work today" />
        </Field>

        <Field label="Notes">
          <textarea className={`${inputClass} resize-y`} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="General progress notes" />
        </Field>

        {error ? <div className="rounded-[8px] border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger)]">{error}</div> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
          <Button type="button" variant="ghost" onClick={onClose} disabled={createLog.isPending}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={createLog.isPending || !logDate}>
            {createLog.isPending ? "Saving…" : "Save log"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
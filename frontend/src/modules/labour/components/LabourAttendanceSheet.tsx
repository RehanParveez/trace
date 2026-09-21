import { useEffect, useState } from "react";
import {Button, EmptyState, Field, inputClass, Panel, PanelHeader, useToast,
} from "../../organizations/components/OrganizationUi";
import { getApiErrorMessage } from "../../identity";
import { useBulkRecordAttendance, useLabourDeployments } from "../hooks";

interface LabourAttendanceSheetProps {
  projectId: string;
  canManage: boolean;
  onDeploy: () => void;
}

export function LabourAttendanceSheet({ projectId, canManage, onDeploy }: LabourAttendanceSheetProps) {
  const deploymentsQuery = useLabourDeployments(projectId);
  const bulkAttendance = useBulkRecordAttendance(projectId);
  const { showToast } = useToast();

  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [values, setValues] = useState<Record<string, string>>({});

  const activeDeployments = (deploymentsQuery.data ?? []).filter((d) => d.status === "ACTIVE");

  useEffect(() => {
    setValues({});
  }, [date]);

  function submit() {
    const entries = activeDeployments
      .filter((d) => values[d.id] !== undefined && values[d.id] !== "")
      .map((d) => ({ deployment_id: d.id, attendance_date: date, units_present: Number(values[d.id]) }));

    if (entries.length === 0) {
      showToast({ tone: "info", title: "Nothing to save", description: "Enter attendance for at least one deployment." });
      return;
    }

    bulkAttendance.mutate(entries, {
      onSuccess: (result) => showToast({ tone: "success", title: `Attendance saved (${result.created} new, ${result.updated} updated)` }),
      onError: (error) => showToast({ tone: "error", title: "Couldn't save attendance", description: getApiErrorMessage(error, "Please try again.") }),
    });
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow="DAILY ATTENDANCE"
        title="Mark attendance"
        description="For a named worker: 1 = present, 0.5 = half day, 0 = absent. For a headcount category, enter the number present."
        action={canManage ? <Button variant="secondary" size="sm" onClick={onDeploy}>Deploy worker / category</Button> : null}
      />

      <div className="p-5 sm:p-6">
        <Field label="Date">
          <input type="date" className={`${inputClass} max-w-[200px]`} value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>

        {activeDeployments.length === 0 ? (
          <div className="mt-4">
            <EmptyState icon="users" title="No active deployments" description="Deploy a worker or a headcount category to this project to start marking attendance." />
          </div>
        ) : (
          <div className="mt-4 space-y-2">
            {activeDeployments.map((deployment) => (
              <div key={deployment.id} className="flex items-center justify-between gap-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5">
                <span className="text-[13px] font-medium text-[var(--color-text-primary)]">
                  {deployment.trade}{deployment.worker_id ? "" : " (headcount)"} — Rs {deployment.daily_rate}/day
                </span>
                <input
                  type="number"
                  step={deployment.worker_id ? "0.5" : "1"}
                  min="0"
                  max={deployment.worker_id ? "1" : undefined}
                  className="w-24 rounded-[6px] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-right text-[13px] outline-none focus:border-[var(--color-trace-gold-dark)]"
                  value={values[deployment.id] ?? ""}
                  onChange={(e) => setValues((current) => ({ ...current, [deployment.id]: e.target.value }))}
                  disabled={!canManage}
                />
              </div>
            ))}
          </div>
        )}

        {canManage && activeDeployments.length > 0 ? (
          <div className="mt-5 flex justify-end border-t border-[var(--color-border)] pt-4">
            <Button variant="primary" disabled={bulkAttendance.isPending} onClick={submit}>
              {bulkAttendance.isPending ? "Saving…" : "Save attendance"}
            </Button>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}